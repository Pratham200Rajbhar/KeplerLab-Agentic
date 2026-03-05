import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as _plt_module
_original_show = _plt_module.show

def _capture_show():
    import io, base64
    buf = io.BytesIO()
    _plt_module.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    print(f"__CHART__:{encoded}")
    _plt_module.close('all')

_plt_module.show = _capture_show

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Generate synthetic 3D scatter data with 3 distinct clusters
np.random.seed(42)

# Cluster 1: centered around (0, 0, 0)
cluster1 = np.random.randn(70, 3) + np.array([0, 0, 0])

# Cluster 2: centered around (3, 3, 3)
cluster2 = np.random.randn(70, 3) + np.array([3, 3, 3])

# Cluster 3: centered around (-3, -3, 3)
cluster3 = np.random.randn(60, 3) + np.array([-3, -3, 3])

# Combine all clusters
data = np.vstack([cluster1, cluster2, cluster3])
labels = np.array([0]*70 + [1]*70 + [2]*60)

# Create 3D scatter plot
fig1 = plt.figure(figsize=(10, 8))
ax1 = fig1.add_subplot(111, projection='3d')
colors = ['red', 'blue', 'green']
for i in range(3):
    mask = labels == i
    ax1.scatter(data[mask, 0], data[mask, 1], data[mask, 2], 
                c=colors[i], label=f'Cluster {i+1}', s=50, alpha=0.7)

ax1.set_xlabel('X axis')
ax1.set_ylabel('Y axis')
ax1.set_zlabel('Z axis')
ax1.set_title('3D Scatter Plot with 3 Clusters')
ax1.legend()
plt.savefig('scatter_3d.png', dpi=150, bbox_inches='tight')
plt.close()

# Generate 3D surface plot of z = sin(sqrt(x²+y²))
x = np.linspace(-5, 5, 100)
y = np.linspace(-5, 5, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(np.sqrt(X**2 + Y**2))

# Create surface plot
fig2 = plt.figure(figsize=(10, 8))
ax2 = fig2.add_subplot(111, projection='3d')
surf = ax2.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none', alpha=0.9)

ax2.set_xlabel('X axis')
ax2.set_ylabel('Y axis')
ax2.set_zlabel('Z axis')
ax2.set_title('3D Surface Plot: z = sin(sqrt(x²+y²))')
fig2.colorbar(surf, ax=ax2, shrink=0.5, aspect=10)
plt.savefig('surface_3d.png', dpi=150, bbox_inches='tight')
plt.close()

# Print confirmation
print("Generated 3D visualizations:")
print("- scatter_3d.png: 3D scatter plot with 200 points in 3 clusters")
print("- surface_3d.png: 3D surface plot of z = sin(sqrt(x²+y²))")