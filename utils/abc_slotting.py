import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

class ABCSlotter:
    """
    A class to perform ABC inventory slotting analysis.
    
    This class encapsulates the logic for calculating ABC classes for inventory items,
    generating a Pareto chart, and providing summary statistics.
    """
    
    def __init__(self):
        """Initializes the ABCSlotter, setting up placeholder attributes."""
        # --- Instance Variables ---
        # These will be populated after the analysis is run.
        self.result_df = None  # The dataframe with the full analysis results.
        self.cumulative_percentage = None  # Array of cumulative value percentages for plotting.
        self.value_percentage = None  # Array of individual item value percentages for plotting.
        self.item_percentage = None  # Array of cumulative item percentages for plotting.
    
    def perform_abc_analysis(self, df, item_column, demand_column, cost_column, 
                            a_cutoff=0.8, b_cutoff=0.95):
        """
        Performs the core ABC analysis on the provided dataframe.

        This method calculates the annual value of each item, sorts them, computes
        cumulative value percentages, and assigns an ABC class based on the defined cutoffs.
        """
        # --- 1. Data Preparation ---
        # Create a copy to avoid modifying the original dataframe passed to the function.
        result_df = df.copy()
        
        # Calculate the total annual value for each item (demand * cost).
        # This is the primary metric for ranking items.
        result_df['annual_value'] = result_df[demand_column] * result_df[cost_column]
        
        # Sort items by their annual value in descending order (most valuable first).
        # `reset_index(drop=True)` creates a clean new index for the sorted dataframe.
        result_df = result_df.sort_values('annual_value', ascending=False).reset_index(drop=True)
        
        # --- 2. Percentage Calculations ---
        # Calculate the total value of all items combined.
        total_value = result_df['annual_value'].sum()
        # Calculate the percentage of total value that each individual item represents.
        result_df['value_percentage'] = result_df['annual_value'] / total_value
        # Calculate the cumulative sum of the value percentage. This is key for the ABC classification.
        result_df['cumulative_value_percentage'] = result_df['value_percentage'].cumsum()
        
        # Calculate the cumulative percentage of items.
        total_items = len(result_df)
        # The item's rank (index + 1) divided by the total number of items.
        result_df['item_percentage'] = (result_df.index + 1) / total_items
        
        # --- 3. ABC Classification ---
        # Start by assigning all items to the lowest class, 'C'.
        result_df['abc_class'] = 'C'
        # Reclassify items as 'B' if their cumulative value is within the B cutoff.
        result_df.loc[result_df['cumulative_value_percentage'] <= b_cutoff, 'abc_class'] = 'B'
        # Reclassify items as 'A' if their cumulative value is within the A cutoff. This overwrites 'B' for the top items.
        result_df.loc[result_df['cumulative_value_percentage'] <= a_cutoff, 'abc_class'] = 'A'
        
        # --- 4. Store Results ---
        # Store the results and key data series as instance variables for later use in plotting and summaries.
        self.result_df = result_df
        self.cumulative_percentage = result_df['cumulative_value_percentage'].values
        self.item_percentage = result_df['item_percentage'].values
        self.value_percentage = result_df['value_percentage'].values
        
        return result_df
    
    def plot_pareto_chart(self, ax=None):
        """
        Plots a Pareto chart showing the ABC analysis results.

        A Pareto chart visually represents the 80/20 rule, showing the value
        contribution of items as bars and the cumulative contribution as a line.
        """
        # Ensure that the analysis has been run before trying to plot.
        if self.result_df is None:
            raise ValueError("No analysis results available. Run perform_abc_analysis first.")
            
        # If no matplotlib axes are provided, create a new figure and axes.
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        # --- Plotting --- 
        # Plot the individual item value percentages as bars.
        ax.bar(self.item_percentage, self.value_percentage, color='skyblue', alpha=0.7, label='Item Value %')
        
        # Create a second y-axis that shares the same x-axis for the cumulative line.
        ax2 = ax.twinx()
        # Plot the cumulative value percentage as a line chart on the second y-axis.
        ax2.plot(self.item_percentage, self.cumulative_percentage, color='red', marker='o', 
                 linestyle='-', linewidth=2, markersize=4, label='Cumulative Value %')
        
        # --- Reference Lines --- 
        # Find the point where the last 'A' item and 'B' item fall on the x-axis.
        a_items_cutoff = self.result_df[self.result_df['abc_class'] == 'A']['item_percentage'].max()
        b_items_cutoff = self.result_df[self.result_df['abc_class'] == 'B']['item_percentage'].max()
        
        # --- Class Labels ---
        # Dynamically position text labels for each class within the plot area.
        y_pos_max = ax.get_ylim()[1] # Get the top of the y-axis for relative positioning.

        # Draw a vertical line and place text for Class A.
        if not pd.isna(a_items_cutoff):
            ax.axvline(x=a_items_cutoff, color='green', linestyle='--', alpha=0.7)
            # Position text in the middle of the 'A' section.
            ax.text(a_items_cutoff / 2, y_pos_max * 0.8, 'Class A', fontsize=12, color='green', ha='center')
        
        # Draw a vertical line and place text for Class B.
        if not pd.isna(b_items_cutoff):
            ax.axvline(x=b_items_cutoff, color='orange', linestyle='--', alpha=0.7)
            # Position text in the middle of the 'B' section.
            ax.text(a_items_cutoff + (b_items_cutoff - a_items_cutoff) / 2, y_pos_max * 0.6, 'Class B', fontsize=12, color='orange', ha='center')

        # Place text for Class C in the middle of its section.
        ax.text(b_items_cutoff + (1 - b_items_cutoff) / 2, y_pos_max * 0.4, 'Class C', fontsize=12, color='gray', ha='center')
        
        # --- Formatting --- 
        ax.set_xlabel('Cumulative Percentage of Items')
        ax.set_ylabel('Percentage of Total Value (by Item)')
        ax2.set_ylabel('Cumulative Percentage of Total Value')
        ax.set_title('ABC Analysis Pareto Chart')
        
        # Set y-axis limits to make the chart readable.
        ax.set_ylim(0, max(self.value_percentage) * 1.1)
        ax2.set_ylim(0, 1.05)
        
        # Add a grid for better readability.
        ax.grid(True, alpha=0.3)
        
        return ax
    
    def get_class_summary(self):
        """
        Calculates and returns summary statistics for each ABC class.

        This includes the number of items, percentage of total items, total value,
        and percentage of total value for each class.
        """
        # Ensure analysis has been run.
        if self.result_df is None:
            raise ValueError("No analysis results available. Run perform_abc_analysis first.")
        
        # --- Aggregation ---
        # Group the results by 'abc_class' and calculate key metrics for each group.
        # .agg() allows calculating multiple statistics at once.
        summary = self.result_df.groupby('abc_class').agg(
            item_count=('abc_class', 'count'),  # Count the number of items in each class.
            total_value=('annual_value', 'sum'),  # Sum the total value of items in each class.
        ).reset_index()
        
        # --- Percentage Calculation ---
        # Calculate the grand totals needed for percentage calculations.
        total_items = len(self.result_df)
        total_value = self.result_df['annual_value'].sum()
        
        # Calculate the percentage of total items and total value for each class.
        summary['item_percentage'] = (summary['item_count'] / total_items) * 100
        summary['value_percentage'] = (summary['total_value'] / total_value) * 100
        
        # --- Formatting ---
        # Reorder columns for a more logical presentation.
        summary = summary[['abc_class', 'item_count', 'item_percentage', 
                          'total_value', 'value_percentage']]
        
        # Ensure the classes are sorted in A, B, C order.
        summary['abc_class'] = pd.Categorical(summary['abc_class'], ['A', 'B', 'C'])
        summary = summary.sort_values('abc_class')

        return summary
