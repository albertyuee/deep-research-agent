from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
import numpy as np

# ================= 1. 连接 Zilliz Cloud =================
ZILLIZ_ENDPOINT = "https://in03-d8eed719467e6e1.serverless.ali-cn-hangzhou.cloud.zilliz.com.cn"  # 替换为你的 Public Endpoint
ZILLIZ_TOKEN = "ae2fa1bb19c61b8c5ea3574c749ebbb1c30433f40fc19e73cdb8da33037e4f3fac34f5dce70448c658ed9273accf57e50df96838"  # 替换为你的 Token

connections.connect(
    alias="default",
    uri=ZILLIZ_ENDPOINT,
    token=ZILLIZ_TOKEN,
    secure=True   # Zilliz Cloud 强制要求 HTTPS
)

print("Connected to Zilliz Cloud")

# ================= 2. 定义 Schema =================
collection_name = "demo_collection"

# 字段定义
id_field = FieldSchema(
    name="id",
    dtype=DataType.INT64,
    is_primary=True,
    auto_id=False
)
vector_field = FieldSchema(
    name="vector",
    dtype=DataType.FLOAT_VECTOR,
    dim=128   # 向量维度，以 128 为例
)
# 可选：标量字段用于过滤
scalar_field = FieldSchema(
    name="category",
    dtype=DataType.VARCHAR,
    max_length=64
)

schema = CollectionSchema(
    fields=[id_field, vector_field, scalar_field],
    description="Demo collection on Zilliz Cloud"
)

# ================= 3. 创建 Collection =================
# 如果同名集合已存在，先删除（谨慎在生产环境使用）
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
    print(f"Deleted existing collection: {collection_name}")

collection = Collection(
    name=collection_name,
    schema=schema,
    using="default"
)
print(f"Collection {collection_name} created")

# ================= 4. 插入数据 =================
# 随机生成 100 条 128 维向量
vectors = np.random.random([100, 128]).tolist()
ids = list(range(100))
categories = [f"cat_{i % 5}" for i in range(100)]  # 5 种分类

data = [ids, vectors, categories]
collection.insert(data)
print(f"Inserted {collection.num_entities} entities")

# ================= 5. 创建索引 (必须，否则搜索性能极差) =================
index_params = {
    "metric_type": "L2",      # 距离度量方式
    "index_type": "IVF_FLAT", # 索引类型
    "params": {"nlist": 128}
}
collection.create_index(
    field_name="vector",
    index_params=index_params
)
print("Index created")

# ================= 6. 加载 Collection 到内存 =================
collection.load()
print("Collection loaded")

# ================= 7. 搜索 =================
# 查询向量：随机生成一个 128 维向量
query_vector = np.random.random([1, 128]).tolist()

# 搜索参数
search_params = {
    "metric_type": "L2",
    "params": {"nprobe": 10}
}

# 不带标量过滤的搜索
results = collection.search(
    data=query_vector,
    anns_field="vector",
    param=search_params,
    limit=5,
    output_fields=["id", "category"]  # 返回额外字段
)

print("\nSearch results (without filter):")
for hits in results:
    for hit in hits:
        print(f"ID: {hit.id}, Distance: {hit.distance}, Category: {hit.entity.get('category')}")

# 带标量过滤的搜索
filter_expr = "category == 'cat_0'"
results_filtered = collection.search(
    data=query_vector,
    anns_field="vector",
    param=search_params,
    limit=3,
    expr=filter_expr,               # 过滤条件
    output_fields=["id", "category"]
)

print("\nSearch results (filtered by category='cat_0'):")
for hits in results_filtered:
    for hit in hits:
        print(f"ID: {hit.id}, Distance: {hit.distance}, Category: {hit.entity.get('category')}")

# ================= 8. 清理（可选） =================
# 如果只是测试，结束后可以删除集合；生产环境不要随意删
# utility.drop_collection(collection_name)
# print(f"Collection {collection_name} dropped")

# 断开连接（可选，程序退出时会自动断开）
connections.disconnect("default")