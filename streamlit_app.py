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
    df = None
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
        
        # Create columns for file upload options
        col1, col2 = st.columns(2)
        
        # File uploader in first column
        with col1:
            uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
        
        # Example file button in second column
        with col2:
            load_example = st.button("📋 Load Example File", use_container_width=True, help="Load a pre-configured example file to test the application")
        
        # Handle example file loading
        if load_example:
            import os
            # Get the absolute path to the example file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            example_file_path = os.path.join(current_dir, "example", "sku_historical_data.csv")
            
            try:
                # Load the example file with semicolon separator
                df = pd.read_csv(example_file_path, sep=';')
                
                # Normalize column names immediately
                df.columns = [col.lower().strip() for col in df.columns]
                
                # Set session state to indicate example file is loaded
                st.session_state['example_loaded'] = True
                st.session_state['df'] = df
                
                st.success("✅ Example file loaded successfully!")
                
                # Clear the uploaded_file to avoid confusion
                uploaded_file = None
                
            except Exception as e:
                st.error(f"❌ Error loading example file: {str(e)}")
                st.info(f"Attempted to load from: {example_file_path}")
                # Reset session state
                if 'example_loaded' in st.session_state:
                    del st.session_state['example_loaded']
                if 'df' in st.session_state:
                    del st.session_state['df']
        
        # Initialize variables for analysis parameters
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
        
        # Get dataframe either from uploaded file or session state
        if uploaded_file is not None:
            try:
                # First check if file is empty
                file_content = uploaded_file.getvalue().decode('utf-8', errors='replace').strip()
                if not file_content:
                    st.error("❌ Error: The uploaded file is empty.")
                    df = None
                else:
                    # Reset the file pointer to the beginning
                    uploaded_file.seek(0)
                    
                    # Try multiple delimiters
                    delimiters = [',', ';', '\t', '|']
                    df = None
                    error_messages = []
                    
                    for delimiter in delimiters:
                        try:
                            # Try with current delimiter
                            uploaded_file.seek(0)  # Reset file pointer
                            temp_df = pd.read_csv(uploaded_file, sep=delimiter, engine='python')
                            
                            # Check if we got more than one column
                            if len(temp_df.columns) > 1:
                                df = temp_df
                                st.success(f"✅ File loaded successfully with '{delimiter}' delimiter")
                                break
                            else:
                                error_messages.append(f"Only found 1 column with '{delimiter}' delimiter")
                        except Exception as e:
                            error_messages.append(f"Failed with '{delimiter}' delimiter: {str(e)}")
                    
                    # If all delimiters failed
                    if df is None:
                        # Try one more time with automatic delimiter detection
                        try:
                            uploaded_file.seek(0)  # Reset file pointer
                            df = pd.read_csv(uploaded_file, sep=None, engine='python')  # Let Python engine detect the separator
                            st.success("✅ File loaded successfully with auto-detected delimiter")
                        except Exception as e:
                            # If all attempts failed, show detailed error
                            error_detail = "\n".join(error_messages)
                            st.error(f"❌ Error: Could not parse the CSV file. Please check the file format.\n\nDetails:\n{error_detail}")
                            
                            # Show a preview of the file content to help diagnose
                            st.error("File preview (first 200 characters):\n" + file_content[:200])
                            df = None
                
                # If we successfully loaded the dataframe
                if df is not None:
                    # Normalize column names to lowercase
                    df.columns = [col.lower().strip() for col in df.columns]
                    
                    # Store in session state
                    st.session_state['df'] = df
                    st.session_state['example_loaded'] = False
                    
                    # Show a preview of the loaded data
                    st.write("Preview of loaded data:")
                    st.dataframe(df.head(3))
                    
            except Exception as e:
                st.error(f"❌ Error: Unexpected error while processing file: {str(e)}")
                df = None
        elif 'example_loaded' in st.session_state and st.session_state['example_loaded'] and 'df' in st.session_state:
            # Use the dataframe from session state if example was loaded
            df = st.session_state['df']
        else:
            df = None
            
        # If we have a valid dataframe, show analysis options
        if df is not None:
            # Convert column names to lowercase for case-insensitive matching
            item_col_lower = item_col.lower()
            demand_col_lower = demand_col.lower()
            cost_col_lower = cost_col.lower()
            
            # Check for required columns
            missing_cols = [col for col in [item_col_lower, demand_col_lower, cost_col_lower] if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                st.write("Please ensure your CSV has these columns (case-insensitive).")
            else:
                # Show data preview
                st.write("### Data Preview")
                st.dataframe(df.head())
                
                # Analysis parameters section
                st.write("### ABC Classification Parameters")
                a_cutoff = st.slider("Class A cutoff (%)", 0, 100, 80)
                b_cutoff = st.slider("Class B cutoff (%)", 0, 100, 95)
                
                # Warehouse location configuration
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
                
                # Create a blue button using Streamlit's native functionality
                # First add the CSS to make the button blue
                st.markdown("""
                <style>
                div.stButton > button:first-child {
                    background-color: blue;
                    color: white;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Then create the button
                run_analysis = st.button("▶️ Run ABC Analysis", use_container_width=True)
    
    # Main analysis section - we've already handled the data preview in the sidebar
    # Only process if run_analysis is True and we have a valid dataframe
    if run_analysis and df is not None:
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
