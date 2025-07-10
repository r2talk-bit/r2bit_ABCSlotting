import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from utils.abc_slotting import ABCSlotter

def main():
    """
    Main function to run the Streamlit application for ABC Inventory Slotting Analysis.

    This function sets up the user interface, handles file uploads, collects user parameters,
    runs the ABC analysis, and displays the results including dataframes, charts, and
    warehouse location assignments.
    """
    # Set the page configuration for a wide layout to make better use of the screen
    st.set_page_config(layout="wide")
    
    # --- Page Title and Instructions ---
    st.title("ABC Inventory Slotting Analysis")
    
    # Display detailed instructions on how to use the tool and what ABC analysis is.
    # This helps users understand the purpose and functionality of the application.
    st.header("Instructions")
    st.write("""
    ### How to use this tool:
    
    1. Upload your CSV file using the sidebar on the left
    2. Adjust the cutoff percentages for ABC classification
    3. Click "Run ABC Analysis"
    4. View the results and download the report
    5. Optionally, upload warehouse location data to assign locations based on ABC classification
    
    ### What is ABC Slotting?
    
    ABC analysis is an inventory categorization method that divides items into three categories:
    - **A items**: High value/priority (typically 80% of value from 20% of items)
    - **B items**: Medium value/priority items
    - **C items**: Low value/priority items
    
    This analysis helps optimize inventory management and warehouse slotting.
    """)
    
    # --- Configuration: Predefined Column Names ---
    # These are the expected column names in the input CSV file.
    # Using variables for these makes the code easier to maintain.
    item_col = "item_id"
    demand_col = "annual_demand"
    cost_col = "unit_cost"
    
    # --- State Initialization ---
    # Initialize session state variables to hold data and control flow across reruns.
    df = None  # Will hold the uploaded or example DataFrame.
    run_analysis = False  # Flag to trigger the analysis when the user clicks the button.
    result_df = None  # Will hold the DataFrame with analysis results.
    
    # --- Sidebar for User Inputs ---
    # The sidebar is used for all user configurations to keep the main area clean for results.
    with st.sidebar:
        st.header("Upload and Configure")
        
        st.write("### 1. Upload Your Inventory Data")
        st.write("Your CSV file must contain the following columns (case-insensitive):")
        st.write(f"- `{item_col}`: A unique identifier for each item.")
        st.write(f"- `{demand_col}`: The total demand for the item over a year.")
        st.write(f"- `{cost_col}`: The cost of a single unit of the item.")
        
        # Use columns to place the file uploader and example button side-by-side for a cleaner UI.
        col1, col2 = st.columns(2)
        
        # The file uploader widget allows users to select a CSV file from their local machine.
        with col1:
            uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
        
        # The example file button provides a way for users to test the app without their own data.
        with col2:
            load_example = st.button("📋 Load Example File", use_container_width=True, help="Load a pre-configured example file to test the application")
        
        # --- Logic for Loading Data ---
        # This block handles the logic for loading the example file if the button is clicked.
        if load_example:
            import os
            # Construct the absolute path to the example file to ensure it's found correctly.
            current_dir = os.path.dirname(os.path.abspath(__file__))
            example_file_path = os.path.join(current_dir, "example", "sku_historical_data.csv")
            
            try:
                # The example file is known to use a semicolon separator.
                df = pd.read_csv(example_file_path, sep=';')
                
                # Best practice: Normalize column names to lowercase and remove whitespace
                # to make them easier to work with.
                df.columns = [col.lower().strip() for col in df.columns]
                
                # Use Streamlit's session state to store the loaded dataframe and a flag.
                # This preserves the data across user interactions (reruns).
                st.session_state['example_loaded'] = True
                st.session_state['df'] = df
                
                st.success("✅ Example file loaded successfully!")
                
                # Set uploaded_file to None to ensure the app uses the example data,
                # not a previously uploaded file.
                uploaded_file = None
                
            except Exception as e:
                st.error(f"❌ Error loading example file: {str(e)}")
                st.info(f"Attempted to load from: {example_file_path}")
                # If loading fails, clear any related session state to prevent issues.
                if 'example_loaded' in st.session_state:
                    del st.session_state['example_loaded']
                if 'df' in st.session_state:
                    del st.session_state['df']
        
        # --- Default Parameter Initialization ---
        # These variables hold the default values for the analysis and warehouse configuration.
        # They will be updated if the user changes them in the UI.
        a_cutoff = 80
        b_cutoff = 95
        deposit = 1
        alleys = 10
        blocks = 10
        levels = 4
        positions = 10
        a_alleys = [1, 2]
        b_alleys = [3, 4, 5]
        c_alleys = list(range(6, 11))
        run_analysis = False
        
        # --- Data Loading from User Upload ---
        # This block executes if a user has uploaded a file.
        if uploaded_file is not None:
            try:
                # --- File Validation and Parsing ---
                # Read the entire file content to check if it's empty.
                # Decoding with 'replace' prevents errors from unusual characters.
                file_content = uploaded_file.getvalue().decode('utf-8', errors='replace').strip()
                if not file_content:
                    st.error("❌ Error: The uploaded file is empty.")
                    df = None
                else:
                    # The file has content, so reset the pointer to the beginning for reading.
                    uploaded_file.seek(0)
                    
                    # --- Robust Delimiter Detection ---
                    # To handle various CSV formats, we try a list of common delimiters.
                    delimiters = [',', ';', '\t', '|']
                    df = None
                    error_messages = []
                    
                    for delimiter in delimiters:
                        try:
                            # Reset pointer before each read attempt.
                            uploaded_file.seek(0)
                            temp_df = pd.read_csv(uploaded_file, sep=delimiter, engine='python')
                            
                            # A valid CSV should have more than one column.
                            if len(temp_df.columns) > 1:
                                df = temp_df  # Success!
                                st.success(f"✅ File loaded successfully with '{delimiter}' delimiter")
                                break  # Exit the loop once a valid delimiter is found.
                            else:
                                error_messages.append(f"Only found 1 column with '{delimiter}' delimiter")
                        except Exception as e:
                            error_messages.append(f"Failed with '{delimiter}' delimiter: {str(e)}")
                    
                    # --- Fallback and Final Error Handling ---
                    # If the loop finishes and df is still None, no delimiter worked.
                    if df is None:
                        # As a last resort, let pandas try to auto-detect the separator.
                        try:
                            uploaded_file.seek(0)
                            df = pd.read_csv(uploaded_file, sep=None, engine='python')
                            st.success("✅ File loaded successfully with auto-detected delimiter")
                        except Exception as e:
                            # If all attempts failed, provide a comprehensive error message.
                            error_detail = "\n".join(error_messages)
                            st.error(f"❌ Error: Could not parse the CSV file. Please check the file format.\n\nDetails:\n{error_detail}")
                            
                            # Showing a preview of the file can help the user diagnose the issue.
                            st.error("File preview (first 200 characters):\n" + file_content[:200])
                            df = None
                
                # If a dataframe was successfully loaded from the user's file...
                if df is not None:
                    # Normalize column names to ensure consistency (lowercase, no extra spaces).
                    df.columns = [col.lower().strip() for col in df.columns]
                    
                    # Store the dataframe in the session state to persist it across reruns.
                    # Also, explicitly set 'example_loaded' to False.
                    st.session_state['df'] = df
                    st.session_state['example_loaded'] = False
                    
                    # Show the user a small preview of their data to confirm it loaded correctly.
                    st.write("Preview of loaded data:")
                    st.dataframe(df.head(3))
                    
            except Exception as e:
                st.error(f"❌ Error: Unexpected error while processing file: {str(e)}")
                df = None
        
        # --- Retrieve DataFrame from Session State ---
        # If the example was loaded in a previous run, retrieve it from session state.
        elif 'example_loaded' in st.session_state and st.session_state['example_loaded'] and 'df' in st.session_state:
            df = st.session_state['df']
        else:
            # If no file is uploaded and no example is loaded, df remains None.
            df = None
            
        # --- Display Analysis Configuration ---
        # This section only appears if a dataframe (df) is available.
        if df is not None:
            # --- Column Validation ---
            # Before proceeding, ensure the required columns exist in the dataframe.
            # We check against the lowercase versions for case-insensitivity.
            item_col_lower = item_col.lower()
            demand_col_lower = demand_col.lower()
            cost_col_lower = cost_col.lower()
            
            # Create a list of required columns that are not found in the dataframe.
            missing_cols = [col for col in [item_col_lower, demand_col_lower, cost_col_lower] if col not in df.columns]
            
            if missing_cols:
                # If any columns are missing, show an error and stop.
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                st.write("Please ensure your CSV has these columns (case-insensitive).")
            else:
                # --- Configuration UI (if columns are valid) ---
                st.write("### Data Preview")
                st.dataframe(df.head())
                
                # --- ABC Classification Parameters ---
                st.write("### 2. ABC Classification Parameters")
                # Sliders for the user to define the percentage cutoffs for A and B classes.
                a_cutoff = st.slider("Class A cutoff (%): Cumulative value percentage for A items", 0, 100, 80)
                b_cutoff = st.slider("Class B cutoff (%): Cumulative value percentage for A and B items", 0, 100, 95)
                
                # --- Warehouse Configuration ---
                st.write("### 3. Warehouse Configuration")
                st.write("Define the structure of the warehouse.")
                
                # Number inputs for the user to define the physical layout of the warehouse.
                deposit = st.number_input("Number of deposits", min_value=1, max_value=9, value=1)
                alleys = st.number_input("Number of alleys per deposit", min_value=1, max_value=99, value=10)
                blocks = st.number_input("Number of blocks per alley", min_value=1, max_value=99, value=10)
                levels = st.number_input("Number of levels per block", min_value=1, max_value=99, value=4)
                positions = st.number_input("Number of positions per level", min_value=1, max_value=99, value=10)
                
                # --- ABC Slotting Strategy ---
                st.write("### 4. ABC Slotting Strategy")
                st.write("Assign specific alleys to each inventory class.")
                # Multiselect widgets to let the user assign which alleys are for A, B, or C items.
                a_alleys = st.multiselect("A-class alleys (highest value)", options=list(range(1, int(alleys)+1)), default=[1, 2])
                b_alleys = st.multiselect("B-class alleys (medium value)", options=list(range(1, int(alleys)+1)), default=[3, 4, 5])
                c_alleys = st.multiselect("C-class alleys (lowest value)", options=list(range(1, int(alleys)+1)), default=list(range(6, int(alleys)+1)))
                
                # --- Action Button ---
                # Use st.markdown to inject custom CSS for styling the button.
                # This is a common trick to customize the appearance of Streamlit widgets.
                st.markdown("""
                <style>
                div.stButton > button:first-child {
                    background-color: blue;
                    color: white;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # The main button that triggers the analysis. When clicked, `run_analysis` becomes True.
                run_analysis = st.button("▶️ Run ABC Analysis", use_container_width=True)
    
    # --- Main Analysis Block ---
    # This block runs only when the user clicks the 'Run Analysis' button and a dataframe is available.
    if run_analysis and df is not None:
            # --- Data Preparation and Validation ---
            try:
                # It's a good practice to work on a copy of the dataframe to avoid unintended side effects.
                analysis_df = df.copy()
                
                # Convert demand and cost columns to numeric types. `errors='coerce'` is crucial as it
                # will turn any non-numeric values (like text) into Not a Number (NaN).
                analysis_df[demand_col_lower] = pd.to_numeric(analysis_df[demand_col_lower], errors='coerce')
                analysis_df[cost_col_lower] = pd.to_numeric(analysis_df[cost_col_lower], errors='coerce')
                
                # Remove any rows that have NaN in the critical demand or cost columns.
                analysis_df = analysis_df.dropna(subset=[demand_col_lower, cost_col_lower])
                
                # Check if any valid data remains after cleaning.
                if len(analysis_df) == 0:
                    st.error("No valid numeric data found in the required columns. Please check your data.")
                elif len(analysis_df) < len(df):
                    # Inform the user if some rows were discarded.
                    st.warning(f"Some rows ({len(df) - len(analysis_df)}) were removed due to non-numeric values in the demand or cost columns.")
                
                # --- Perform ABC Analysis ---
                # Initialize our custom ABCSlotter class from the utils module.
                abc_slotter = ABCSlotter()
                
                # Call the main analysis function, passing the cleaned dataframe and user-defined parameters.
                # Note: Cutoffs are converted from percentages (e.g., 80) to decimals (e.g., 0.80).
                result_df = abc_slotter.perform_abc_analysis(
                    analysis_df, 
                    item_column=item_col_lower,
                    demand_column=demand_col_lower,
                    cost_column=cost_col_lower,
                    a_cutoff=a_cutoff/100,
                    b_cutoff=b_cutoff/100
                )
                
                # --- Display Analysis Results ---
                st.write("### ABC Classification Results")
                st.dataframe(result_df)
                
                # --- Display Pareto Chart ---
                st.write("### Pareto Analysis (80/20 Rule)")
                # Create a matplotlib figure to plot the Pareto chart on.
                fig, ax = plt.subplots(figsize=(7, 4))
                abc_slotter.plot_pareto_chart(ax)
                plt.tight_layout()  # Ensures the chart fits well within the figure area.
                st.pyplot(fig)  # Display the matplotlib figure in Streamlit.
                
                # --- Display Summary Statistics ---
                st.write("### Summary Statistics by Class")
                # Get a summary dataframe from the slotter and display it.
                summary = abc_slotter.get_class_summary()
                st.dataframe(summary)
                
                # --- Warehouse Location Assignment ---
                st.write("### Warehouse Location Assignments")
                st.write("""
                Items are assigned warehouse locations based on their ABC class to optimize picking routes.
                Locations are in the format `d.aa.bb.ll.pp` (deposit.alley.block.level.position).
                """)
                # Create a dictionary to easily access the list of alleys for each class.
                class_to_alleys = {
                    'A': a_alleys,
                    'B': b_alleys,
                    'C': c_alleys
                }
                
                # Sort items first by class (A, B, C) and then by their value in descending order.
                # This ensures that within each class, the most valuable items are processed first,
                # allowing them to be assigned the most optimal (e.g., closest) locations.
                result_df = result_df.sort_values(['abc_class', 'annual_value'], ascending=[True, False])
                
                # A set is used to keep track of assigned locations for fast lookups (O(1) complexity)
                # to prevent assigning the same location to multiple items.
                used_locations = set()
                
                def assign_optimized_location(row, rank_within_class):
                    """
                    Calculates an optimized warehouse location for an item.

                    This function assigns a location based on the item's ABC class and its rank
                    (by value) within that class. The goal is to place high-value (A) items
                    in the most accessible locations (e.g., lowest-numbered alleys, blocks, levels).

                    Args:
                        row (pd.Series): The row of the dataframe for the item.
                        rank_within_class (int): The rank of the item within its class (0-indexed).

                    Returns:
                        str: The formatted warehouse location string (e.g., "1.01.01.01.01")
                             or an error message if no location is available.
                    """
                    abc_class = row['abc_class']
                    available_alleys = class_to_alleys.get(abc_class, [])
                    
                    if not available_alleys:
                        return "No location available for this class"
                    
                    # Strategy: For 'A' items, always start in the very first available alley.
                    # For 'B' and 'C', distribute them across their assigned alleys.
                    if abc_class == 'A':
                        available_alleys = sorted(available_alleys)
                    
                    # --- Location Calculation Algorithm ---
                    # This algorithm translates a single rank number into a 5-part location code.
                    d = 1  # Default deposit is 1.
                    
                    # Distribute items cyclically among the available alleys for the class.
                    alley_index = rank_within_class % len(available_alleys)
                    aa = available_alleys[alley_index]
                    
                    # Determine the item's overall position index within its assigned alley.
                    total_positions_per_alley = blocks * levels * positions
                    position_rank = rank_within_class // len(available_alleys)
                    
                    # If we run out of space in deposit 1, move to the next deposit.
                    if position_rank >= total_positions_per_alley:
                        d = (position_rank // total_positions_per_alley) + 1
                        position_rank = position_rank % total_positions_per_alley
                    
                    # Calculate block, level, and position, prioritizing lower numbers (more accessible).
                    bb = (position_rank // (levels * positions)) + 1
                    remaining = position_rank % (levels * positions)
                    ll = (remaining // positions) + 1
                    pp = (remaining % positions) + 1
                    
                    # Format the location code with leading zeros for consistency.
                    location = f"{d}.{aa:02d}.{bb:02d}.{ll:02d}.{pp:02d}"
                    
                    # --- Collision Handling ---
                    # If the calculated location is already taken (e.g., due to complex alley assignments),
                    # find the next available spot. This is a simple linear probing approach.
                    attempts = 0
                    while location in used_locations and attempts < 1000: # Safety break
                        pp += 1
                        if pp > positions: # Next level
                            pp = 1; ll += 1
                        if ll > levels: # Next block
                            ll = 1; bb += 1
                        if bb > blocks: # Next alley
                            bb = 1
                            alley_index = (alley_index + 1) % len(available_alleys)
                            aa = available_alleys[alley_index]
                        if alley_index == 0 and bb == 1 and ll == 1 and pp == 1: # Cycled all alleys, move to next deposit
                            d += 1
                        
                        location = f"{d}.{aa:02d}.{bb:02d}.{ll:02d}.{pp:02d}"
                        attempts += 1
                    
                    if location in used_locations:
                        return "Collision: No available location found"
                    
                    used_locations.add(location) # Mark location as used
                    return location
                
                # --- Apply Location Assignment ---
                # Create a temporary column 'rank_within_class' to store the value-based rank of each item inside its class.
                result_df['rank_within_class'] = result_df.groupby('abc_class').cumcount()
                
                # Apply the assignment function to each row of the dataframe.
                result_df['warehouse_location'] = result_df.apply(
                    lambda row: assign_optimized_location(row, row['rank_within_class']), 
                    axis=1
                )
                
                # The ranking column is no longer needed, so it's dropped.
                result_df = result_df.drop('rank_within_class', axis=1)
                
                # Display the final dataframe with the new 'warehouse_location' column.
                st.write("#### Items with Assigned Warehouse Locations")
                st.dataframe(result_df)
                
                # --- Download Report ---
                st.write("### Download Report")
                st.write("Click below to download the full analysis with warehouse locations as a CSV file.")
                # Convert the final dataframe to a CSV string.
                csv = result_df.to_csv(index=False, sep=';')
                # Use Streamlit's download button to offer the CSV to the user.
                st.download_button(
                    label="⬇️ Download ABC Analysis with Locations",
                    data=csv,
                    file_name="abc_analysis_with_locations.csv",
                    mime="text/csv",
                    key="download-csv",
                    help="Download the complete ABC analysis with warehouse locations as a CSV file"
                )
            except Exception as e:
                st.error(f"An error occurred during analysis: {str(e)}")
    else:
        st.info("👈 Please upload your inventory data CSV file using the sidebar to begin.")

if __name__ == "__main__":
    main()
