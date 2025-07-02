import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

class ABCSlotter:
    """
    A class to perform ABC inventory slotting analysis.
    
    ABC analysis is a method of categorizing inventory items based on their value or importance:
    - A items: High value/importance (typically top 80% of value)
    - B items: Medium value/importance (typically next 15% of value)
    - C items: Low value/importance (typically last 5% of value)
    """
    
    def __init__(self):
        self.result_df = None
        self.cumulative_percentage = None
        self.value_percentage = None
        self.item_percentage = None
    
    def perform_abc_analysis(self, df, item_column, demand_column, cost_column, 
                            a_cutoff=0.8, b_cutoff=0.95):
        """
        Perform ABC analysis on the provided dataframe.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Input dataframe with inventory data
        item_column : str
            Name of the column containing item identifiers
        demand_column : str
            Name of the column containing annual demand/usage
        cost_column : str
            Name of the column containing unit cost
        a_cutoff : float, optional (default=0.8)
            Cutoff percentage for Class A items (0.8 = 80%)
        b_cutoff : float, optional (default=0.95)
            Cutoff percentage for Class B items (0.95 = 95%)
            
        Returns:
        --------
        pandas.DataFrame
            Original dataframe with added ABC classification columns
        """
        # Create a copy of the dataframe to avoid modifying the original
        result_df = df.copy()
        
        # Calculate annual value (demand * cost)
        result_df['annual_value'] = result_df[demand_column] * result_df[cost_column]
        
        # Sort by annual value in descending order
        result_df = result_df.sort_values('annual_value', ascending=False).reset_index(drop=True)
        
        # Calculate cumulative value and percentages
        total_value = result_df['annual_value'].sum()
        result_df['value_percentage'] = result_df['annual_value'] / total_value
        result_df['cumulative_value_percentage'] = result_df['value_percentage'].cumsum()
        
        # Calculate item percentages
        total_items = len(result_df)
        result_df['item_percentage'] = (result_df.index + 1) / total_items
        
        # Assign ABC classes
        result_df['abc_class'] = 'C'
        result_df.loc[result_df['cumulative_value_percentage'] <= b_cutoff, 'abc_class'] = 'B'
        result_df.loc[result_df['cumulative_value_percentage'] <= a_cutoff, 'abc_class'] = 'A'
        
        # Store results for plotting
        self.result_df = result_df
        self.cumulative_percentage = result_df['cumulative_value_percentage'].values
        self.item_percentage = result_df['item_percentage'].values
        self.value_percentage = result_df['value_percentage'].values
        
        return result_df
    
    def plot_pareto_chart(self, ax=None):
        """
        Plot a Pareto chart showing the ABC analysis results.
        
        Parameters:
        -----------
        ax : matplotlib.axes.Axes, optional
            Axes object to plot on. If None, a new figure and axes will be created.
            
        Returns:
        --------
        matplotlib.axes.Axes
            The axes containing the plot
        """
        if self.result_df is None:
            raise ValueError("No analysis results available. Run perform_abc_analysis first.")
            
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot the value percentage as bars
        ax.bar(self.item_percentage, self.value_percentage, color='skyblue', alpha=0.7)
        
        # Plot the cumulative percentage as a line
        ax2 = ax.twinx()
        ax2.plot(self.item_percentage, self.cumulative_percentage, color='red', marker='o', 
                 linestyle='-', linewidth=2, markersize=4)
        
        # Add reference lines for A, B, C cutoffs
        a_items = self.result_df[self.result_df['abc_class'] == 'A']['item_percentage'].max()
        b_items = self.result_df[self.result_df['abc_class'] == 'B']['item_percentage'].max()
        
        if not pd.isna(a_items):
            ax.axvline(x=a_items, color='green', linestyle='--', alpha=0.7)
            ax.text(a_items + 0.01, 0.01, 'A', fontsize=12, color='green')
        
        if not pd.isna(b_items):
            ax.axvline(x=b_items, color='orange', linestyle='--', alpha=0.7)
            ax.text(b_items + 0.01, 0.01, 'B', fontsize=12, color='orange')
        
        # Set labels and title
        ax.set_xlabel('Percentage of Items')
        ax.set_ylabel('Value Percentage')
        ax2.set_ylabel('Cumulative Value Percentage')
        ax.set_title('ABC Analysis Pareto Chart')
        
        # Set y-axis limits
        ax.set_ylim(0, max(self.value_percentage) * 1.1)
        ax2.set_ylim(0, 1.05)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        return ax
    
    def get_class_summary(self):
        """
        Get summary statistics for each ABC class.
        
        Returns:
        --------
        pandas.DataFrame
            Summary statistics by ABC class
        """
        if self.result_df is None:
            raise ValueError("No analysis results available. Run perform_abc_analysis first.")
        
        # Group by ABC class and calculate statistics
        summary = self.result_df.groupby('abc_class').agg(
            item_count=('abc_class', 'count'),
            total_value=('annual_value', 'sum'),
        ).reset_index()
        
        # Calculate percentages
        total_items = len(self.result_df)
        total_value = self.result_df['annual_value'].sum()
        
        summary['item_percentage'] = summary['item_count'] / total_items * 100
        summary['value_percentage'] = summary['total_value'] / total_value * 100
        
        # Reorder columns
        summary = summary[['abc_class', 'item_count', 'item_percentage', 
                          'total_value', 'value_percentage']]
        
        return summary
