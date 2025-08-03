"""Default configuration values."""

from pathlib import Path

# Default configuration file locations
DEFAULT_CONFIG_LOCATIONS = [
    Path.home() / ".shard-md" / "config.yaml",
    Path.cwd() / ".shard-md" / "config.yaml",
    Path.cwd() / "shard-md.yaml",
]

# Default YAML configuration template
DEFAULT_CONFIG_YAML = """# Shard Markdown Configuration
chromadb:
  host: localhost
  port: 8000
  ssl: false
  timeout: 30
  auth_token: null

chunking:
  default_size: 1000
  default_overlap: 200
  method: structure
  respect_boundaries: true
  max_tokens: null

processing:
  batch_size: 10
  max_workers: 4
  recursive: false
  pattern: "*.md"
  include_frontmatter: true
  include_path_metadata: true

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: null
  max_file_size: 10485760
  backup_count: 5

custom_metadata: {}
plugins: []
"""

# Environment variable mappings
ENV_VAR_MAPPINGS = {
    "CHROMA_HOST": "chromadb.host",
    "CHROMA_PORT": "chromadb.port", 
    "CHROMA_SSL": "chromadb.ssl",
    "CHROMA_AUTH_TOKEN": "chromadb.auth_token",
    "SHARD_MD_CHUNK_SIZE": "chunking.default_size",
    "SHARD_MD_CHUNK_OVERLAP": "chunking.default_overlap",
    "SHARD_MD_BATCH_SIZE": "processing.batch_size",
    "SHARD_MD_MAX_WORKERS": "processing.max_workers",
    "SHARD_MD_LOG_LEVEL": "logging.level",
}