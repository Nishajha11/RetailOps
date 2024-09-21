import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

order_details = pd.read_csv('order_details.csv')
pizza_data = pd.read_csv('pizzas.csv')

pizza_sales = order_details.groupby('pizza_id')['quantity'].sum().reset_index()
pizza_sales = pd.merge(pizza_sales, pizza_data[['pizza_id', 'name']], on='pizza_id', how='left')

# Select relevant features (only quantity)
features = pizza_sales[['quantity']]

# Normalize the features
scaler = MinMaxScaler()
features_scaled = scaler.fit_transform(features)

# Train the k-NN model
k = 6  # 5 nearest neighbors + the pizza itself
model = NearestNeighbors(n_neighbors=k, metric='euclidean')
model.fit(features_scaled)

# Function to recommend top 5 pizzas being sold
def recommend_top_pizzas():
    # Find the indices of the top 5 pizzas being sold
    distances, indices = model.kneighbors(features_scaled)
    top_pizzas_indices = indices[0][1:]  # Exclude the first index, which corresponds to the pizza itself
    
    # Create lists to store pizza names and quantities sold
    pizza_names = []
    quantities_sold = []
    for idx in top_pizzas_indices:
        pizza_names.append(pizza_sales.iloc[idx]['name'])
        quantities_sold.append(pizza_sales.iloc[idx]['quantity'])

    # Plot the table
    fig, ax = plt.subplots()
    ax.axis('tight')
    ax.axis('off')
    table_data = []
    for i, (name, quantity) in enumerate(zip(pizza_names, quantities_sold), start=1):
        table_data.append([i, name, quantity])
    ax.table(cellText=table_data, colLabels=["Rank", "Pizza Name", "Quantity Sold"], loc='center')
    plt.show()

# Recommend top 5 pizzas being sold
recommend_top_pizzas()