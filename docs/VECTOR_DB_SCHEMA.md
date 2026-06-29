# Vector DB Schema

**Technology:** Qdrant 1.9  
**Purpose:** Semantic similarity for player embeddings and rule retrieval  
**Collections:** `player_embeddings`, `human_rules`

---

## Collection 1: `player_embeddings`

**Purpose:** Find semantically similar players for "players like X" queries and ownership estimation grouping.

### Configuration

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType

client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

client.create_collection(
    collection_name="player_embeddings",
    vectors_config=VectorParams(
        size=128,            # 128-dimensional embedding
        distance=Distance.COSINE
    )
)
```

### Embedding Construction

A player embedding is a 128-dim vector derived from their feature profile:

```python
def build_player_embedding(player: Player, features: RollingFeature) -> np.ndarray:
    """
    Combine rolling stats + role + style into a fixed-size embedding.
    Not a neural embedding — a structured feature vector normalised to unit sphere.
    """
    raw = np.array([
        features.fp_avg_10 / 100.0,
        features.fp_ceiling / 200.0,
        features.fp_consistency,
        features.avg_runs_10 / 80.0,
        features.avg_sr_10 / 200.0,
        features.avg_wickets_10 / 5.0,
        features.avg_economy_10 / 15.0,
        features.fp_30plus_rate,
        ROLE_ENCODING[player.primary_role] / 3.0,
        BATTING_STYLE_ENCODING[player.batting_style] / 1.0,
        BOWLING_STYLE_ENCODING[player.bowling_style] / 4.0,
        # ... pad to 128 dims with venue and matchup features
    ], dtype=np.float32)
    # Zero-pad to 128
    padded = np.zeros(128, dtype=np.float32)
    padded[:len(raw)] = raw
    # L2 normalise
    norm = np.linalg.norm(padded)
    return padded / (norm + 1e-8)
```

### Payload Schema

```python
{
    "player_id": "uuid",              # FK to player table
    "full_name": "Virat Kohli",
    "cricsheet_key": "Kohli, V",
    "primary_role": "BAT",
    "nationality": "India",
    "is_active": True,
    "fp_avg_10": 58.7,
    "fp_ceiling": 116.0,
    "match_type": "T20",
    "last_updated": "2026-06-25",
}
```

### Typical Queries

```python
# Find 5 players most similar to Virat Kohli for substitution suggestions
results = client.search(
    collection_name="player_embeddings",
    query_vector=kohli_embedding,
    query_filter=Filter(must=[
        FieldCondition(key="primary_role", match=MatchValue(value="BAT")),
        FieldCondition(key="is_active", match=MatchValue(value=True)),
    ]),
    limit=5,
    with_payload=True
)
```

---

## Collection 2: `human_rules`

**Purpose:** Semantic search for rules relevant to a match context, enabling fuzzy rule matching beyond exact condition keys.

### Configuration

```python
client.create_collection(
    collection_name="human_rules",
    vectors_config=VectorParams(
        size=768,            # Sentence embedding dimension (all-MiniLM-L6-v2)
        distance=Distance.COSINE
    )
)
```

### Rule Embedding

Each rule's description + condition is embedded as a sentence:

```python
from sentence_transformers import SentenceTransformer

encoder = SentenceTransformer("all-MiniLM-L6-v2")

def embed_rule(rule: HumanRule) -> np.ndarray:
    text = f"{rule.description}. Condition: {json.dumps(rule.condition_json)}"
    return encoder.encode(text, normalize_embeddings=True)
```

### Payload Schema

```python
{
    "rule_id": "RULE-0001",
    "rule_type": "player",
    "player_key": "Kohli, V",
    "impact_score": 22,
    "confidence": 0.87,
    "description": "Virat Kohli averages significantly higher while chasing in T20s",
    "is_active": True,
    "match_types": ["T20", "IPL"],
}
```

### Typical Queries

```python
# Find rules semantically related to "chasing match at Wankhede with dew"
query_embedding = encoder.encode(
    "batter performing in a chasing match at Wankhede stadium with dew factor",
    normalize_embeddings=True
)
results = client.search(
    collection_name="human_rules",
    query_vector=query_embedding,
    query_filter=Filter(must=[
        FieldCondition(key="is_active", match=MatchValue(value=True))
    ]),
    score_threshold=0.75,   # Only return highly relevant rules
    limit=10,
    with_payload=True
)
```

---

## Index Configuration

```python
# Enable payload indexing for filtered searches
client.create_payload_index(
    collection_name="player_embeddings",
    field_name="primary_role",
    field_schema=PayloadSchemaType.KEYWORD
)
client.create_payload_index(
    collection_name="player_embeddings",
    field_name="is_active",
    field_schema=PayloadSchemaType.BOOL
)
client.create_payload_index(
    collection_name="human_rules",
    field_name="is_active",
    field_schema=PayloadSchemaType.BOOL
)
client.create_payload_index(
    collection_name="human_rules",
    field_name="player_key",
    field_schema=PayloadSchemaType.KEYWORD
)
```

---

## Data Volume Estimates

| Collection | Points | Vector Size | Estimated Storage |
|------------|--------|------------|------------------|
| `player_embeddings` | ~8,000 active players × 3 formats | 128 dims × 4 bytes | ~12 MB |
| `human_rules` | ~200 rules | 768 dims × 4 bytes | ~0.6 MB |
| **Total** | | | **~13 MB** |

Qdrant free tier (1 GB storage) is sufficient for MVP.

---

## Sync Strategy

Player embeddings rebuilt weekly (Sunday 3 AM IST):

```bash
python scripts/build_player_embeddings.py --format T20
```

Rules re-indexed whenever a rule is created/updated via admin API.
