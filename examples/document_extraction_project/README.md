# Document Extraction with ZenML

A focused, runnable example of document extraction using ZenML's artifact store and prompt management system.

## Prerequisites

```bash
# Install required dependencies
pip install -r requirements.txt

# Set up OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"

# Initialize ZenML
zenml init
```

## Project Structure

```
document_extraction_project/
├── pipelines/
│   └── document_extraction_pipeline.py  # Main extraction pipeline
├── steps/
│   ├── process_document_batch.py        # Document processing with artifact store
│   ├── filter_processable_documents.py  # Document filtering
│   ├── extract_batch_data.py           # LLM-based data extraction
│   └── validate_batch_results.py       # Output validation
├── prompts/
│   └── invoice_prompts.py              # Invoice extraction prompts
├── schemas/
│   └── invoice_schema.py               # Pydantic schemas for invoices
├── sample_documents/
│   ├── sample_invoice_1.txt            # Sample invoice document
│   ├── sample_invoice_2.txt            # Sample invoice document
│   └── sample_invoice_3.txt            # Sample invoice document
├── utils/
│   ├── document_utils.py               # Document processing utilities
│   └── api_utils.py                    # API helper functions
└── main.py                   # Main script to run the pipeline
```

## Quick Start

1. **Set up environment**:
   ```bash
   cd examples/document_extraction_project
   export OPENAI_API_KEY="your-key-here"
   ```

2. **Run document extraction on sample data**:
   ```bash
   python main.py --document sample_documents/ --type invoice
   ```

3. **Run on specific document**:
   ```bash
   python main.py --document sample_documents/sample_invoice_1.txt --type invoice
   ```

4. **Save results to file**:
   ```bash
   python main.py --document sample_documents/ --output results.json
   ```

## Features Demonstrated

- ✅ **ZenML Artifact Store Integration**: Universal file access (local, S3, GCS, etc.)
- ✅ **Real OpenAI API Integration**: Uses actual GPT-4 for document extraction
- ✅ **ZenML Prompt Artifacts**: Versioned prompts with variable templating
- ✅ **Pydantic Schema Validation**: Structured output validation
- ✅ **Batch Processing**: Process multiple documents efficiently
- ✅ **Quality Metrics**: Completeness and confidence scoring
- ✅ **Error Handling**: Robust error handling and reporting
- ✅ **Sample Documents**: Ready-to-use invoice examples

## Sample Documents

The project includes three sample invoice documents in `sample_documents/`:

- `sample_invoice_1.txt` - Software services invoice from ACME Corporation
- `sample_invoice_2.txt` - Database migration services from DataTech Solutions
- `sample_invoice_3.txt` - Cloud services annual billing from CloudServ Inc.

## Sample Output

```json
{
  "summary_stats": {
    "total_documents": 3,
    "successful_extractions": 3,
    "success_rate": 1.0,
    "schema_compliance_rate": 1.0
  },
  "validated_results": [
    {
      "file_path": "/path/to/sample_invoice_1.txt",
      "is_valid": true,
      "validated_data": {
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-01-15",
        "vendor_name": "ACME Corporation",
        "total_amount": 8680.00,
        "line_items": [...]
      }
    }
  ]
}
```