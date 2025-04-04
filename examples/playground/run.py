import os
import tempfile
from pathlib import Path

from zenml import pipeline, step
from path_materializer import PathMaterializer

@step(output_materializers=PathMaterializer)
def generate_log_and_diff_files() -> Path:
    """Creates sample log and Git diff files for testing the PathMaterializer.
    
    This represents Andrei's real-world use case of generating logs and Git diffs.
    """
    # Create a temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="zenml-logs-"))
    
    # Create a sample log file
    log_content = """
2024-04-04 09:15:23 INFO [ModelTrainer] Starting model training with config: {batch_size: 32, epochs: 100}
2024-04-04 09:15:25 INFO [DataLoader] Loading training data from s3://data/training.parquet
2024-04-04 09:15:30 INFO [DataLoader] Loading validation data from s3://data/validation.parquet
2024-04-04 09:15:35 WARNING [ModelTrainer] Found 15 missing values in feature 'customer_age'
2024-04-04 09:15:36 INFO [ModelTrainer] Imputing missing values with median
2024-04-04 09:16:10 INFO [ModelTrainer] Starting training loop
2024-04-04 09:16:15 INFO [ModelTrainer] Epoch 1/100, Loss: 0.724, Val Loss: 0.692
2024-04-04 09:16:20 INFO [ModelTrainer] Epoch 2/100, Loss: 0.685, Val Loss: 0.671
...
2024-04-04 10:45:12 INFO [ModelTrainer] Epoch 100/100, Loss: 0.341, Val Loss: 0.362
2024-04-04 10:45:15 INFO [ModelTrainer] Training completed successfully
2024-04-04 10:45:20 INFO [ModelEvaluator] Model accuracy: 0.882
2024-04-04 10:45:25 INFO [ModelEvaluator] Model F1 score: 0.865
2024-04-04 10:45:30 INFO [ModelSaver] Saving model to s3://models/customer_churn_v2.pkl
2024-04-04 10:45:35 INFO [Pipeline] Pipeline execution completed successfully
"""
    (temp_dir / "pipeline.log").write_text(log_content)
    
    # Create a sample Git diff file
    git_diff_content = """diff --git a/model/trainer.py b/model/trainer.py
index 8a7b6d9..2c4fd82 100644
--- a/model/trainer.py
+++ b/model/trainer.py
@@ -45,7 +45,7 @@ class ModelTrainer:
         self.learning_rate = config.get('learning_rate', 0.001)
         self.batch_size = config.get('batch_size', 32)
         self.epochs = config.get('epochs', 50)
-        self.early_stopping = config.get('early_stopping', False)
+        self.early_stopping = config.get('early_stopping', True)
         self.patience = config.get('patience', 5)
         
     def train(self, X_train, y_train, X_val, y_val):
@@ -58,6 +58,8 @@ class ModelTrainer:
         model.compile(
             optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
             loss='binary_crossentropy',
-            metrics=['accuracy']
+            metrics=['accuracy', 'AUC', 'Precision', 'Recall']
         )
+        
+        logger.info(f"Training model with {X_train.shape[0]} samples")
         return model.fit(X_train, y_train, batch_size=self.batch_size, epochs=self.epochs)
"""
    (temp_dir / "model_changes.diff").write_text(git_diff_content)
    
    # Create a README file
    readme_content = """# Pipeline Output Files

This directory contains output files from the model training pipeline:

- **pipeline.log**: Contains the complete logs from the training run
- **model_changes.diff**: Shows the Git diff of changes made to the model code

These files are generated automatically by the pipeline and can be downloaded directly from the ZenML dashboard.
"""
    (temp_dir / "README.md").write_text(readme_content)
    
    return temp_dir

@step
def process_output_files(directory: Path) -> str:
    """Process the files in the directory.
    
    In a real pipeline, this might do something with the files,
    but for this example we just report on them.
    """
    # Print information about the directory
    print(f"Processing directory: {directory}")
    
    if directory.exists():
        file_info = []
        for item in sorted(directory.glob("**/*")):
            if item.is_file():
                file_info.append(f"- {item.relative_to(directory)} ({item.stat().st_size} bytes)")
        
        summary = f"Found {len(file_info)} files in the output directory:\n" + "\n".join(file_info)
        print(summary)
        return summary
    
    return "Directory not found"

@pipeline
def file_download_demo_pipeline():
    """Pipeline that demonstrates the PathMaterializer with self-contained download capability."""
    directory = generate_log_and_diff_files()
    process_output_files(directory)
    
if __name__ == "__main__":
    file_download_demo_pipeline()