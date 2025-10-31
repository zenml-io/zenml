# FiftyOne Annotator

FiftyOne is a powerful open-source computer vision dataset visualization and evaluation platform. It provides tools for dataset exploration, model evaluation, and annotation workflows. FiftyOne supports various computer vision tasks including:

* Object Detection (bounding boxes, evaluation metrics)
* Image Classification (labels, confidence scores)
* Semantic Segmentation (masks, pixel-level analysis)
* Dataset Management (filtering, sampling, visualization)
* Model Analysis (error analysis, performance metrics)

## When would you want to use it?

If you need to visualize, analyze, or annotate computer vision datasets as part of your ML workflow, FiftyOne provides an excellent solution. The FiftyOne annotator class in this example demonstrates how to:

- **Load and manage datasets** from popular sources (COCO, Open Images, etc.) with proper class mapping
- **Export datasets to training formats** (YOLO, COCO JSON, etc.) with correct COCO 80-class mapping
- **Run model inference** and import predictions with confidence thresholds
- **Evaluate model performance** with detailed metrics (mAP@0.5, mAP@0.75, per-class analysis)
- **Launch interactive dashboards** for dataset exploration with custom port support
- **Handle multiple image formats** (URLs, local files, base64 data URIs)

This annotator implementation follows the ZenML annotator pattern, making it easy to refactor into a full ZenML integration later.

**🔧 Key Problem Solved**: Fixes the critical COCO class mapping issue where FiftyOne exports datasets with sequential IDs (0-N) instead of proper COCO class IDs (0-79), which causes catastrophic training failure with 0 mAP/precision/recall.

## How to use it?

The `FiftyOneAnnotator` class provides a clean API that encapsulates all FiftyOne functionality:

### Basic Usage

```python
from annotators import FiftyOneAnnotator

# Initialize the annotator
annotator = FiftyOneAnnotator()

# Load a dataset (with proper COCO class mapping)
dataset = annotator.add_dataset(
    dataset_source="coco-2017",
    split="validation",
    max_samples=5
)

# Export to YOLO format for training (fixes class mapping issue!)
export_path = annotator.export_to_yolo_format(
    dataset_name="coco-2017-validation-5samples",
    export_dir="./data/coco_subset"
)

# Run model inference and add predictions
annotator.run_inference_and_add_predictions(
    dataset_name="coco-2017-validation-5samples",
    model=trained_yolo_model,
    confidence_threshold=0.25
)

# Evaluate predictions vs ground truth
metrics = annotator.evaluate_predictions(
    dataset_name="coco-2017-validation-5samples"
)
# Example output: {'mAP_50': None, 'mAP_75': None, 'class_metrics': {...}, 'total_samples': 5}

# Launch interactive dashboard with custom port
session = annotator.launch(
    dataset_name="coco-2017-validation-5samples",
    port=8080  # Custom port support
)
```

### Real Example from Testing

Here's what actually happened when we tested the annotator:

```bash
# Training with 5 samples, 1 epoch
python run.py --train --samples 5 --epochs 1

# Results achieved:
# ✅ mAP@50: 0.799, mAP@50-95: 0.624
# ✅ Precision: 0.885, Recall: 0.700
# ✅ Successfully detected: 4 persons, 1 bus, 1 stop sign

# Launch dashboard
python launch_fiftyone.py coco-2017-validation-5samples --port 8080
# ✅ Dataset: 5 samples with 5 labeled (100% prediction coverage)
```

### Configuration

The annotator accepts a configuration object:

```python
from annotators import FiftyOneAnnotator, FiftyOneAnnotatorConfig

config = FiftyOneAnnotatorConfig(
    default_port=8080,
    auto_launch=True  # Automatically open browser
)

annotator = FiftyOneAnnotator(config)
```

## Core Methods

The `FiftyOneAnnotator` class follows the ZenML annotator pattern with these key methods:

### Dataset Management
- `get_datasets()` - Get all available FiftyOne datasets
- `get_dataset_names()` - Get list of dataset names
- `get_dataset_stats(dataset_name)` - Get labeled/unlabeled sample counts
- `add_dataset(**kwargs)` - Register/load a new dataset
- `get_dataset(dataset_name)` - Load an existing dataset
- `delete_dataset(dataset_name)` - Delete a dataset

### Data Access
- `get_labeled_data(dataset_name)` - Get samples with predictions
- `get_unlabeled_data(dataset_name)` - Get samples without predictions

### Annotation Workflow
- `export_to_yolo_format()` - Export dataset for training
- `run_inference_and_add_predictions()` - Add model predictions to dataset
- `evaluate_predictions()` - Compute evaluation metrics

### Visualization
- `get_url()` - Get FiftyOne App URL
- `get_url_for_dataset()` - Get dataset-specific URL
- `launch()` - Start FiftyOne App session

## Integration with ZenML Steps

The annotator is used throughout the computer vision example:

### Data Loading (`steps/data_loader.py`)
```python
# Initialize annotator and load COCO dataset
annotator = FiftyOneAnnotator()
dataset = annotator.add_dataset(
    dataset_source="coco-2017",
    split=split,
    max_samples=max_samples
)

# Export for YOLO training with correct class mapping
export_path = annotator.export_to_yolo_format(
    dataset_name=dataset_name,
    export_dir=export_dir
)
```

### Dashboard Launching (`launch_fiftyone.py`)
```python
# Use annotator for improved dataset management
annotator = FiftyOneAnnotator()

# Get dataset statistics
labeled_count, unlabeled_count = annotator.get_dataset_stats(dataset_name)

# Launch with proper configuration
session = annotator.launch(dataset_name=dataset_name, port=port)
```

## Helper Functions

The annotator includes several utility functions:

### COCO Class Mapping Fix

**⚠️ Critical Issue**: FiftyOne exports COCO datasets with sequential class IDs (0, 1, 2, ...) but YOLO models expect the original COCO class IDs (0-79 with gaps). This mismatch causes catastrophic training failure.

**✅ Solution**: The `COCO_CLASSES` constant provides the correct 80-class mapping:

```python
# Before: Training fails with 0 mAP (wrong class mapping)
# FiftyOne export: class IDs 0-11 for 12 classes

# After: Training succeeds with proper mAP (correct class mapping)
annotator.export_to_yolo_format(
    dataset_name="coco-2017-validation-5samples",
    export_dir="./data/coco_subset",
    # classes=COCO_CLASSES automatically applied
)
# YOLO export: proper COCO class IDs 0-79
```

### Evaluation Metrics

The `evaluate_predictions()` method computes comprehensive metrics at different IoU thresholds:

```python
results = annotator.evaluate_predictions("coco-2017-validation-5samples")

# Example real output from our testing:
{
    'mAP_50': None,           # Overall mAP at IoU 0.5
    'mAP_75': None,           # Overall mAP at IoU 0.75
    'class_metrics': {
        'person': {'mAP': None, 'precision': 1.000, 'recall': 1.000},
        'sheep': {'mAP': None, 'precision': 1.000, 'recall': 1.000},
        'sports ball': {'mAP': None, 'precision': 1.000, 'recall': 1.000},
        'bowl': {'mAP': None, 'precision': 0.000, 'recall': 0.000},
        # ... per-class breakdown
    },
    'total_samples': 5,
    'eval_keys': ['eval_50', 'eval_75']
}
```


## Future Integration

This annotator class is designed for easy refactoring into a full ZenML integration:

1. **Inherit from BaseAnnotator**: Change class definition to extend ZenML's base class
2. **Add Flavor Support**: Create corresponding flavor class for stack registration
3. **Stack Component**: Register as official ZenML stack component
4. **Settings Integration**: Add ZenML settings support for advanced configuration

The current implementation provides all the foundational functionality needed for a complete ZenML FiftyOne integration while remaining usable as a standalone component in this example.

## Learn More

- [FiftyOne Documentation](https://docs.voxel51.com/)
- [FiftyOne GitHub](https://github.com/voxel51/fiftyone)
- [ZenML Annotators Guide](https://docs.zenml.io/component-guide/annotators)
- [Computer Vision Example](../README.md)