import pandas as pd

fi = pd.read_csv("../../reports/gb_v2_feature_importances.csv")
print(fi.head(20))