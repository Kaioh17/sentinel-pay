import joblib
import kagglehub
from kagglehub import KaggleDatasetAdapter
import lightgbm as lgb
from sklearn.model_selection import train_test_split

# Load the dataset using kagglehub
file_path = "creditcard.csv"
df = kagglehub.load_dataset(KaggleDatasetAdapter.PANDAS, "mlg-ulb/creditcardfraud", file_path)

print("Dataset loaded with shape:", df.shape)

# Separate features and target label
# 'Class' is 1 for fraud and 0 for legitimate transactions
X = df.drop(columns=["Class"])
y = df["Class"]

# Split data into training and testing sets with stratification
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Initialize and train the LightGBM model
model = lgb.LGBMClassifier(
    n_estimators=100, learning_rate=0.05, random_state=42, class_weight="balanced"
)

print("Training model...")
model.fit(X_train, y_train)

# Save the model artifact to disk
model_filename = "fraud_model.pkl"
joblib.dump(model, model_filename)
print(f"Model saved successfully to {model_filename}")