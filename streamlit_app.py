import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from utils.abc_slotting import ABCSlotter

def main():
    st.set_page_config(layout="wide")
    st.title("ABC Inventory Slotting Analysis")
    
    # Instructions immediately below the title
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
    
    # Predefined column names
    item_col = "item_id"
    demand_col = "annual_demand"
    cost_col = "unit_cost"
    
    # Initialize variables
    df = st.session_state.get('df', None)
    uploaded_file = st.session_state.get('uploaded_file', None)
    run_analysis = False
    result_df = None
    
    # Sidebar for file upload and parameters
    with st.sidebar:
        st.header("Upload and Configure")
        
        st.write("### Upload your inventory data")
        st.write("Your CSV file should contain the following columns:")
        st.write(f"- `{item_col}`: Item identifier")
        st.write(f"- `{demand_col}`: Annual demand/usage")
        st.write(f"- `{cost_col}`: Unit cost")
        
        # File uploader for CSV files
        file_upload = st.file_uploader("Choose a CSV file", type=["csv"])
        
        # Update session state if a file is uploaded
        if file_upload is not None:
            uploaded_file = file_upload
            st.session_state['uploaded_file'] = file_upload
        
        # Button to load example file (now below the file uploader)
        if st.button("Load Example Input File", use_container_width=True):
            # Use the example file path
            example_file_path = "example/sku_historical_data.csv"
            try:
                # First try with comma separator (default)
                df = pd.read_csv(example_file_path)
                # Check if we need to use semicolon separator
                if len(df.columns) == 1 and ';' in df.columns[0]:
                    # Try with semicolon separator
                    df = pd.read_csv(example_file_path, sep=';')
                    st.success(f"Loaded example file with semicolon separator: {example_file_path}")
                else:
                    st.success(f"Loaded example file: {example_file_path}")
                
                # Normalize column names for the example file
                df.columns = [col.lower().strip() for col in df.columns]
                
                # Set uploaded_file to a special value to indicate example file is loaded
                uploaded_file = "EXAMPLE_FILE_LOADED"
                
                # Store the dataframe in session state so it persists across reruns
                st.session_state['df'] = df
                st.session_state['uploaded_file'] = uploaded_file
                
                # Force a rerun to show parameters immediately
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error loading example file: {str(e)}")
        
        # Only show the rest of the options if a file is uploaded or example file is loaded
        if uploaded_file is not None:
            # If example file is already loaded, skip this section
            if uploaded_file != "EXAMPLE_FILE_LOADED" and df is None:
                # Try reading with different separators
                try:
                    # First try with comma separator (default)
                    df = pd.read_csv(uploaded_file)
                    if len(df.columns) == 1 and ';' in df.columns[0]:
                        # If we only have one column and it contains semicolons, try with semicolon separator
                        uploaded_file.seek(0)  # Reset file pointer
                        df = pd.read_csv(uploaded_file, sep=';')
                        st.success("Detected semicolon-separated CSV file")
                    
                    # Store dataframe in session state
                    st.session_state['df'] = df
                except Exception as e:
                    st.error(f"Error reading CSV file: {str(e)}")
                    st.info("Try uploading a CSV file with comma or semicolon separators")
                    df = None
                    st.session_state['df'] = None
            
            if df is not None:
                # Debug: Show actual column names
                st.write("### Debug: Actual columns in your CSV file")
                st.write(f"Column names: {list(df.columns)}")
                
                # Check if required columns exist (case-insensitive)
                df.columns = [col.lower().strip() for col in df.columns]  # Normalize column names
                item_col_lower = item_col.lower()
                demand_col_lower = demand_col.lower()
                cost_col_lower = cost_col.lower()
                
                missing_cols = [col for col in [item_col_lower, demand_col_lower, cost_col_lower] if col not in df.columns]
                
                if missing_cols:
                    st.error(f"Missing required columns: {', '.join(missing_cols)}")
                    st.write("Please ensure your CSV has these columns (case-insensitive).")
                else:
                    st.write("### ABC Classification Parameters")
                    a_cutoff = st.slider("Class A cutoff (%)", 0, 100, 80)
                    b_cutoff = st.slider("Class B cutoff (%)", 0, 100, 95)
                    
                    # Warehouse location configuration in sidebar
                    st.write("### Warehouse Configuration")
                    st.write("Configure warehouse locations in format d.aa.bb.ll.pp:")
                    
                    # Warehouse dimensions
                    deposit = st.number_input("Number of deposits", min_value=1, max_value=9, value=1)
                    alleys = st.number_input("Number of alleys per deposit", min_value=1, max_value=99, value=10)
                    blocks = st.number_input("Number of blocks per alley", min_value=1, max_value=99, value=10)
                    levels = st.number_input("Number of levels per block", min_value=1, max_value=99, value=4)
                    positions = st.number_input("Number of positions per level", min_value=1, max_value=99, value=10)
                    
                    # ABC slotting strategy
                    st.write("### ABC Slotting Strategy")
                    a_alleys = st.multiselect("A-class alleys", options=list(range(1, int(alleys)+1)), default=[1, 2])
                    b_alleys = st.multiselect("B-class alleys", options=list(range(1, int(alleys)+1)), default=[3, 4, 5])
                    c_alleys = st.multiselect("C-class alleys", options=list(range(1, int(alleys)+1)), default=list(range(6, int(alleys)+1)))
                    
                    run_analysis = st.button("Run ABC Analysis")
    
    # Main content area
    if (uploaded_file is not None or uploaded_file == "EXAMPLE_FILE_LOADED") and df is not None:
        st.write("### Data Preview")
        st.dataframe(df.head())
        
        if run_analysis:
            # Convert demand and cost columns to numeric
            try:
                # Make a copy of the dataframe to avoid modifying the original
                analysis_df = df.copy()
                
                # Convert columns to numeric, errors='coerce' will convert non-numeric values to NaN
                analysis_df[demand_col_lower] = pd.to_numeric(analysis_df[demand_col_lower], errors='coerce')
                analysis_df[cost_col_lower] = pd.to_numeric(analysis_df[cost_col_lower], errors='coerce')
                
                # Drop rows with NaN values after conversion
                analysis_df = analysis_df.dropna(subset=[demand_col_lower, cost_col_lower])
                
                if len(analysis_df) == 0:
                    st.error("No valid numeric data found in the required columns. Please check your data.")
                elif len(analysis_df) < len(df):
                    st.warning(f"Some rows ({len(df) - len(analysis_df)}) were removed due to non-numeric values in the demand or cost columns.")
                
                # Initialize the ABC slotter
                abc_slotter = ABCSlotter()
                
                # Run the analysis
                result_df = abc_slotter.perform_abc_analysis(
                    analysis_df, 
                    item_column=item_col_lower,
                    demand_column=demand_col_lower,
                    cost_column=cost_col_lower,
                    a_cutoff=a_cutoff/100,
                    b_cutoff=b_cutoff/100
                )
                
                # Display results
                st.write("### ABC Classification Results")
                st.dataframe(result_df)
                
                # Display charts
                st.write("### Pareto Analysis")
                fig, ax = plt.subplots(figsize=(7, 4))  # Optimal size for Pareto chart visualization
                abc_slotter.plot_pareto_chart(ax)
                plt.tight_layout()  # Adjust padding to eliminate empty space
                st.pyplot(fig)
                
                # Display summary statistics
                st.write("### Summary Statistics by Class")
                summary = abc_slotter.get_class_summary()
                st.dataframe(summary)
                
                # Automatically assign warehouse locations
                st.write("### Warehouse Location Assignments")
                st.write("""
                Items have been assigned warehouse locations based on their ABC classification.
                Locations are in the format d.aa.bb.ll.pp where:
                - d = deposit number
                - aa = alley number
                - bb = block number
                - ll = level number
                - pp = position number
                """)
                # Create a dictionary to map ABC classes to alleys
                class_to_alleys = {
                    'A': a_alleys,
                    'B': b_alleys,
                    'C': c_alleys
                }
                
                # Sort items by annual_value within each ABC class
                # This ensures highest value items get the best locations
                result_df = result_df.sort_values(['abc_class', 'annual_value'], ascending=[True, False])
                
                # Create a tracking dictionary for used locations
                used_locations = set()
                
                # Function to generate a warehouse location based on ABC class and value
                def assign_optimized_location(row, rank_within_class):
                    abc_class = row['abc_class']
                    
                    # Get available alleys for this class
                    available_alleys = class_to_alleys.get(abc_class, [])
                    
                    if not available_alleys:
                        return "No location available"
                    
                    # For A class: use lowest alley numbers first
                    # For B and C: distribute more evenly
                    if abc_class == 'A':
                        available_alleys = sorted(available_alleys)  # Use lowest alley numbers first
                    
                    # Calculate optimal position components based on rank within class
                    # This ensures highest value items get most accessible locations
                    d = 1  # Start with deposit 1 for highest value items
                    
                    # Cycle through available alleys
                    alley_index = rank_within_class % len(available_alleys)
                    aa = available_alleys[alley_index]
                    
                    # Calculate block, level, position based on rank
                    # Lower numbers = better accessibility
                    total_positions = blocks * levels * positions
                    position_rank = rank_within_class // len(available_alleys)
                    
                    if position_rank >= total_positions:
                        # If we run out of positions in deposit 1, move to deposit 2, etc.
                        d = (position_rank // total_positions) + 1
                        position_rank = position_rank % total_positions
                    
                    # Calculate block, level, position
                    # Prioritize lower blocks, then lower levels, then lower positions
                    bb = (position_rank // (levels * positions)) + 1
                    remaining = position_rank % (levels * positions)
                    ll = (remaining // positions) + 1
                    pp = (remaining % positions) + 1
                    
                    # Format as d.aa.bb.ll.pp
                    location = f"{d}.{aa:02d}.{bb:02d}.{ll:02d}.{pp:02d}"
                    
                    # Check if location is already used
                    attempts = 0
                    while location in used_locations and attempts < 100:
                        # Try next position
                        pp += 1
                        if pp > positions:
                            pp = 1
                            ll += 1
                        if ll > levels:
                            ll = 1
                            bb += 1
                        if bb > blocks:
                            bb = 1
                            alley_index = (alley_index + 1) % len(available_alleys)
                            aa = available_alleys[alley_index]
                        if alley_index == 0:  # We've cycled through all alleys
                            d += 1
                        
                        location = f"{d}.{aa:02d}.{bb:02d}.{ll:02d}.{pp:02d}"
                        attempts += 1
                    
                    # If we couldn't find an unused location after many attempts
                    if location in used_locations:
                        return "No available location"
                    
                    # Mark this location as used
                    used_locations.add(location)
                    return location
                
                # Group by ABC class to get rank within each class
                result_df['rank_within_class'] = result_df.groupby('abc_class').cumcount()
                
                # Apply the function to generate locations
                result_df['warehouse_location'] = result_df.apply(
                    lambda row: assign_optimized_location(row, row['rank_within_class']), 
                    axis=1
                )
                
                # Drop the temporary ranking column
                result_df = result_df.drop('rank_within_class', axis=1)
                
                # Display the results
                st.write("#### Items with Assigned Warehouse Locations")
                st.dataframe(result_df)
                
                # Download section with prominent button
                st.write("### Download Report")
                st.write("Click below to download your ABC Slotting analysis report with warehouse locations:")
                csv = result_df.to_csv(index=False, sep=';')
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
