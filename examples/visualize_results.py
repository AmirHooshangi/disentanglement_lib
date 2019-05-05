import matplotlib.pyplot as plt

from disentanglement_lib.utils import aggregate_results
df = aggregate_results.load_aggregated_json_results("/home/velorin/disentanglement_lib/examples/example_output/results.json")
print(type(df))

df.plot(kind='scatter',x='num_children',y='num_pets',color='red')
plt.show()