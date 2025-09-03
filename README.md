# FormFiller

This script automates the submission of randomized responses to a multi-page Google Form. It is designed for testing, data generation, or load simulation purposes.

## Features
- Randomly generates answers for each question based on predefined options and rules.
- Handles multi-page Google Forms, including hidden tokens and cumulative answers.
- Submits multiple responses with configurable delays between submissions.
- Saves HTML responses for debugging if a submission fails.

## Requirements
- Python 3.7+
- `requests` library

Install dependencies:
```bash
pip install requests
```

## Usage
Run the script from the command line:
```bash
python fill6.py
```
By default, it will submit 3 randomized responses with a delay of 0.7–1.6 seconds between each.

You can customize the number of submissions and delay:
```python
submit_many(n=10, delay=(1, 2))
```

## How It Works
- **Form Configuration:**
  - Set the Google Form ID and entry IDs for each question.
  - Define possible answer options for each question.
- **Random Answer Generation:**
  - Answers are randomly selected, with logic to enforce constraints (e.g., if vision is "ไม่มีปัญหา", aids must be "ไม่ใช้").
- **Submission Logic:**
  - Fetches the first page to collect hidden tokens.
  - Builds and submits payloads for each page, updating tokens as needed.
  - Checks for successful submission and saves response HTML if errors occur.

## Customization
- To use with a different Google Form, update the `FORM_ID` and entry IDs at the top of `fill6.py`.
- Adjust answer options or logic as needed for your form structure.

## Disclaimer
This script is for educational, testing, or research purposes only. Do not use it to spam or abuse Google Forms.

## Author
- [patthananb](https://github.com/patthananb)
