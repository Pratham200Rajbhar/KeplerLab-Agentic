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
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
from collections import Counter
import re

# Generate a synthetic paragraph about ML, AI, data science, Python, and neural networks
paragraph = """
Machine learning (ML) is a transformative subset of artificial intelligence (AI) that enables computers to learn from data without explicit programming. By leveraging algorithms and statistical models, machine learning systems identify patterns and make predictions with increasing accuracy. Data science, an interdisciplinary field, combines domain expertise, programming skills, and knowledge of mathematics and statistics to extract insights from structured and unstructured data. Python has emerged as the dominant programming language for both machine learning and data science due to its simplicity, readability, and rich ecosystem of libraries such as scikit-learn, TensorFlow, PyTorch, and pandas. Neural networks, inspired by the human brain, form the backbone of deep learning — a powerful ML approach capable of handling complex tasks like image recognition, natural language processing, and autonomous decision-making. These networks consist of interconnected layers of nodes (neurons) that process input data through weighted connections, adjusting parameters via backpropagation to minimize prediction errors. As computational power grows and datasets expand, AI and ML continue to revolutionize industries including healthcare, finance, transportation, and education. Python's versatility, supported by active communities and robust frameworks, accelerates innovation in neural network research and deployment. Ultimately, the synergy between data science methodologies, AI capabilities, and Python's practicality drives the next generation of intelligent systems that shape our digital future.
"""

# Clean and tokenize
words = re.findall(r'\b[a-zA-Z]{3,}\b', paragraph.lower())
stopwords = set(STOPWORDS)
stopwords.update(['python', 'ml', 'ai', 'the', 'and', 'of', 'to', 'in', 'for', 'is', 'are', 'that', 'by', 'with', 'as', 'from', 'can', 'such', 'this', 'our', 'we', 'their', 'its'])

filtered_words = [w for w in words if w not in stopwords]

# Create word frequency dictionary
word_freq = Counter(filtered_words)

# Generate word cloud with circular mask
try:
    # Create circular mask
    mask = np.array([[1 if (i-50)**2 + (j-50)**2 <= 50**2 else 0 
                      for j in range(100)] for i in range(100)])
    
    wordcloud = WordCloud(width=800, height=800, 
                          background_color='white',
                          mask=mask,
                          contour_width=3,
                          contour_color='steelblue',
                          stopwords=stopwords,
                          max_words=150,
                          colormap='viridis').generate_from_frequencies(word_freq)
    
    plt.figure(figsize=(10, 10))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title('Word Cloud: Machine Learning, AI, Data Science & Neural Networks', fontsize=16)
    plt.savefig('word_cloud.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print("Word cloud saved as 'word_cloud.png'")
    
except Exception as e:
    # Fallback: create frequency bar chart if wordcloud fails
    top_words = word_freq.most_common(15)
    words, counts = zip(*top_words)
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(words, counts, color='steelblue')
    plt.xlabel('Words', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Top 15 Words in ML/AI/Data Science Paragraph', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Add value labels on bars
    for bar, count in zip(bars, counts):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                 str(count), ha='center', va='bottom', fontsize=10)
    
    plt.savefig('word_frequency_chart.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Word cloud generation failed ({str(e)}). Frequency bar chart saved as 'word_frequency_chart.png'")
    
# Print summary
print(f"Total words processed: {len(words)}")
print(f"Unique words after filtering: {len(word_freq)}")
print(f"Top 5 words: {word_freq.most_common(5)}")