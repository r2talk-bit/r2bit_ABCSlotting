# ABC Inventory Slotting Analysis

This Streamlit application performs ABC inventory slotting analysis on your inventory data. ABC analysis is a method of categorizing inventory items based on their value or importance:

- **A items**: High value/importance (typically top 80% of value)
- **B items**: Medium value/importance (typically next 15% of value)
- **C items**: Low value/importance (typically last 5% of value)

## Project Structure

```
r2bit_ABCSlotting/
├── streamlit_app.py      # Main Streamlit application
├── utils/
│   └── abc_slotting.py   # ABC slotting algorithm implementation
├── requirements.txt      # Project dependencies
└── README.md             # This file
```

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the Streamlit application:
   ```
   streamlit run streamlit_app.py
   ```

2. Upload a CSV file containing your inventory data with columns for:
   - Item ID
   - Annual demand/usage
   - Unit cost

3. Select the appropriate columns for analysis
4. Adjust the ABC classification parameters if needed
5. Run the analysis to view results and download the classified data

## Features

- Interactive Pareto chart visualization
- Customizable A/B/C classification thresholds
- Summary statistics by class
- Downloadable results in CSV format
