# Deterministic risk assessment (Layer 1)

## What "deterministic" means here

The Layer 1 service decides if a transaction is safe to continue.
It does not estimate a probability.
It applies fixed rules to stored facts.
If the facts are equal, the decision is equal.
Time, random numbers, and request order do not change the result.

The service returns two values for each transaction:

- `decision`: `APPROVE`, `REVIEW`, or `DECLINE`.
- `rule_triggered`: the name of the rule that caused the decision, or `null` when no rule fired.

`is_fraud` is not part of the answer.
It is ground truth, and it arrives later with a chargeback.
The Layer 2 model score is also not part of this answer.
The Layer 2 model runs only when Layer 1 returns `APPROVE`.

## The three checks

Each check is a pure function in [risk.py](../backend/app/service/risk.py).
A pure function reads only its arguments and has no side effects.
This is the reason the result is repeatable.
It is also the reason the checks are easy to test.

| Check | Input | `DECLINE` | `REVIEW` |
| --- | --- | --- | --- |
| Account | status and risk tier of the user | `FROZEN`, `SUSPENDED`, `CLOSED`, or unknown user | `RESTRICTED`, or tier `HIGH` |
| Country | country code of the transaction | `BLOCKED` | `REQUIRES_STEP_UP` |
| Entity | IP address, device fingerprint, email domain, card hash | `BLOCK_IMMEDIATELY` | `FLAG_FOR_REVIEW` |

The service runs all three checks and keeps the worst result.
The order of severity is `DECLINE`, then `REVIEW`, then `APPROVE`.
When two results have the same severity, the first one wins.
The order is account, then country, then entity.
Inside the entity check, the order is IP address, device fingerprint, email domain, and card hash.
A fixed order is necessary.
Without it, the `rule_triggered` value could change between two runs.

A `rule_triggered` value names the rule and the value that fired it.
Examples are `ACCOUNT_FROZEN`, `COUNTRY_BLOCKED:KP`, and `ENTITY_BLOCK:IP_ADDRESS`.
The entity rule names the type of entity, but not the entity value.
This keeps card hashes and device fingerprints out of logs and responses.

## Where the facts come from

Postgres is the source of truth for three tables: `account_risk_status`, `country_restrictions`, and `entity_blocklist`.
Redis holds a small copy of these tables.
Redis keeps only the columns that the checks read.

| Redis key | Value | Expiry |
| --- | --- | --- |
| `acct:{user_id}` | status, risk tier, and email domain, joined with `\|` | none |
| `country:{code}` | restriction type | none |
| `ent:{type}:{value}` | severity | from `expires_at` |
| `idem:{transaction_id}` | the stored answer | 24 hours |
| `risk:warm` | flag that shows the copy is loaded | twice the reload period |

Redis stores a country only when it is restricted.
A missing country key means "no restriction".
A missing entity key means "not on the blocklist".
This keeps the copy small.
It also creates a risk, which the next section describes.

## How a request flows

1. The caller sends `POST /transactions` with the transaction data.
2. The service reads all facts from Redis with one `MGET` command.
3. The service reads the blocklist entry for the email domain with a second command.
   The domain comes from the account entry, so the service cannot read it earlier.
4. The pure checks run and produce the answer.
5. The service sends the answer to the caller.
6. After the response, a background task saves the transaction row to Postgres.

The service does not wait for Postgres.
The assessment starts before the write and finishes before the write starts.
The row is saved once, with the decision already known.
This avoids a `PENDING` row and a second update.

The logs show the time of each step.
One line per request shows the method, path, status, and milliseconds.
One more line per assessment shows the data source and the milliseconds.
The source is `redis`, `postgres`, `idempotent`, or `none`.

## The caller

The frontend calls `POST /transactions` once for each simulated transaction.
There is no separate verify route.
The page builds the request from the selected scenario and the open account.
A scenario sets the merchant, IP address, device fingerprint, and card hash.
A scenario can also set a country.
If it does not, the page uses the country of the account.

The response is only `decision` and `rule_triggered`.
Layer 2 is not set up yet.
When Layer 1 returns `APPROVE`, the page tells the user that the model has not scored the transaction.
The stored decision stays `APPROVE` in this case, so it is not final until Layer 2 exists.

The server saves the row after it sends the response.
The page therefore asks again for the transaction list until the new row appears.
It stops after about one second.

The user cannot enter an amount.
Each scenario has a fixed amount.
Layer 1 does not read the amount, so the amount does not change any rule.

`backend/scripts/seed_mock.py` adds the accounts and the risk rows that the scenarios hit.
The Redis copy picks them up at the next reload, or at the next restart.
The seed skips an account that already exists.
To change the mock accounts, reset the database first.

## Mock accounts and scenarios

The user chooses two things: an account and a scenario.
The account controls the account rule and the email domain rule.
The scenario controls the country rule and the IP address, device, and card rules.

| Account | State | Result for a clean scenario |
| --- | --- | --- |
| Amara Okafor, Lukas Brandt | active, low risk | `APPROVE` |
| James Whitfield | frozen | `DECLINE`, `ACCOUNT_FROZEN` |
| Sofia Marin | suspended | `DECLINE`, `ACCOUNT_SUSPENDED` |
| Priya Raman | restricted | `REVIEW`, `ACCOUNT_RESTRICTED` |
| Carlos Mendes | high risk tier | `REVIEW`, `ACCOUNT_RISK_TIER_HIGH` |
| Tunde Bakare | email domain flagged | `REVIEW`, `ENTITY_FLAG:EMAIL_DOMAIN` |
| Ivan Petrov | email domain blocked | `DECLINE`, `ENTITY_BLOCK:EMAIL_DOMAIN` |

| Scenario | Result for a clean account |
| --- | --- |
| Morning coffee, Rent payment | `APPROVE` |
| Foreign cash withdrawal | `REVIEW`, `COUNTRY_STEP_UP:RU` |
| New device transfer | `REVIEW`, `ENTITY_FLAG:DEVICE_FINGERPRINT` |
| Purchase through a proxy | `REVIEW`, `ENTITY_FLAG:IP_ADDRESS` |
| Previously disputed card | `REVIEW`, `ENTITY_FLAG:CARD_HASH` |
| Sanctioned country transfer | `DECLINE`, `COUNTRY_BLOCKED:KP` |
| Account takeover | `DECLINE`, `ENTITY_BLOCK:DEVICE_FINGERPRINT` |
| Gift card drain | `DECLINE`, `ENTITY_BLOCK:IP_ADDRESS` |
| Card testing | `DECLINE`, `ENTITY_BLOCK:CARD_HASH` |

A restricted account shows the precedence rules.
Priya Raman with a blocked country gives `DECLINE`, because `DECLINE` is more severe than `REVIEW`.
James Whitfield with a blocked country gives `ACCOUNT_FROZEN`, because both are `DECLINE` and the account check comes first.

## Failure behavior

A fraud check must not approve a transaction because a store is down.
The service handles each failure as follows.

**Redis is down or slow.**
The client waits at most 50 ms and does not retry.
The service then reads the same facts from Postgres with indexed queries.
After a failure, the service skips Redis for 5 seconds.
This stops each request from paying the timeout again.

**Redis is up but empty.**
This happens after a Redis restart.
A restart removes the `risk:warm` flag, and the service sees that the flag is missing.
The service then reads from Postgres.
Without the flag, an empty Redis would look like "no restrictions" and approve everything.

**Both stores are down.**
The service returns `REVIEW` with the rule `RISK_STORE_UNAVAILABLE`.
It never returns `APPROVE` without facts.

**The user is not found.**
The service returns `DECLINE` with the rule `UNKNOWN_USER`.

**The caller sends the same `transaction_id` again.**
The service returns the first answer from `idem:{transaction_id}`.
The unique constraint on the table stops a second row.

## How the cache stays correct

A job loads every risk row from Postgres into Redis at startup.
It repeats this every 5 minutes.
The job also removes keys that no longer exist in Postgres.
A lock key makes sure that only one worker reloads at a time.

The `risk:warm` flag expires after 10 minutes.
If the reload job stops, the flag expires, and the service reads from Postgres.
The cache cannot become old without anyone noticing.

A new user does not exist in Redis until the next reload.
For such a user, the service reads Postgres once and stores the result.

## Trade-offs

**Staleness of up to 5 minutes.**
A change in Postgres reaches Redis only at the next reload.
A frozen account can still pass for up to 5 minutes.
We accepted this to keep the code small and the write path simple.
To remove the delay, write each risk change to Postgres first, then to Redis, in the same function.
That needs admin endpoints, and none exist yet.

**Two Redis reads, not one.**
The email domain is a property of the user, so it is not known before the first read.
The second read costs one more round trip, about 0.2 ms on a local network.
We could precompute the domain verdict inside the account entry.
That would make the entity result older than the other results, and it would differ from the Postgres path.
We chose equal behavior on both paths.

**Cached data for every user.**
The reload job caches all users, not only restricted ones.
This gives the fast path for every user.
The memory use grows with the number of users.
Change to read-through caching only when the user count makes this too large.

**Saving after the response.**
The caller gets the answer faster.
If the background write fails, the row is lost.
The service logs the error but does not retry.
The decision itself is not lost, because `idem:` holds it for 24 hours.
Add an outbox table if losing a row is not acceptable.

**Fail closed means more reviews.**
During a double outage, every transaction goes to `REVIEW`.
This protects against fraud and costs manual work.
We chose this because an approved fraud is more expensive than a delayed good payment.

**One idempotency key store.**
If Redis is down, the `idem:` key is not available.
A retry then runs the checks again.
The result is the same unless the facts changed, and the unique constraint still stops a duplicate row.

**Normalization on write is the writer's job.**
Stored entity values must be lower case with no spaces.
The reload job normalizes them for Redis.
The Postgres path compares the stored text directly, to keep the index usable.
A value stored in a different form can match in Redis and miss in Postgres.

## Database changes

The tables use `create_all`, which does not change existing tables.
An existing development database needs a reset or a migration.
The changes are:

- `users`: the columns `account_status` and `risk_tier` are removed.
  `account_risk_status` is now the only source.
- `account_risk_status.user_id`: now an integer with a foreign key to `users.id`.
- `entity_blocklist`: new unique constraint on `(entity_type, entity_value)`.
- `transaction`: new `country_code` and `card_hash` columns, and `risk_score` can be null.
- `decision` uses one enum everywhere: `APPROVE`, `REVIEW`, `DECLINE`.
  The old `STEP_UP` value is gone.

## Startup and connections

The service opens all pooled Postgres connections at startup.
No request pays the connection and authentication time.
The pool size is set with `DB_POOL_SIZE`.
The app does not open a database session for routes that do not use one.
A session is not a connection, but the removed global dependency did work for every route for no reason.

## How to check it

`tests/test_risk.py` covers the pure rules, the severity order, the Postgres failover, and the double outage.
Run it with `pytest backend/tests`.
