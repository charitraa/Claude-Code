"""
MCP Resource Handlers
Handles resource management, streaming, and caching
"""

import asyncio
import logging
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class FileSystemResourceProvider:
    """
    Provider for file system resources
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize file system resource provider

        Args:
            base_path: Base path for resolving relative paths
        """
        self.base_path = base_path or Path.cwd()

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a file system resource

        Args:
            uri: Resource URI (file://path or relative path)

        Returns:
            Resource contents
        """
        try:
            # Parse URI
            if uri.startswith("file://"):
                file_path = Path(uri[7:])
            else:
                file_path = self.base_path / uri

            # Resolve path
            file_path = file_path.resolve()

            # Security check: ensure path is within base path
            try:
                file_path.relative_to(self.base_path.resolve())
            except ValueError:
                raise ValueError(f"Access denied: path outside base directory")

            # Check if file exists
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Check if it's a file
            if not file_path.is_file():
                raise ValueError(f"Not a file: {file_path}")

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "application/octet-stream"

            # Read file content
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError(f"File too large: {file_path.stat().st_size} bytes")

            if mime_type.startswith("text/"):
                # Read as text
                content = file_path.read_text(encoding="utf-8")
                return {
                    "uri": uri,
                    "mimeType": mime_type,
                    "text": content
                }
            else:
                # Read as binary (base64 encoded)
                import base64
                content = file_path.read_bytes()
                return {
                    "uri": uri,
                    "mimeType": mime_type,
                    "blob": base64.b64encode(content).decode("ascii")
                }

        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
            raise

    async def list_resources(self, path: str = "") -> List[Dict[str, Any]]:
        """
        List resources in a directory

        Args:
            path: Directory path (relative to base path)

        Returns:
            List of resource definitions
        """
        try:
            # Resolve path
            if path.startswith("file://"):
                dir_path = Path(path[7:])
            else:
                dir_path = self.base_path / path

            dir_path = dir_path.resolve()

            # Security check
            try:
                dir_path.relative_to(self.base_path.resolve())
            except ValueError:
                raise ValueError(f"Access denied: path outside base directory")

            # Check if directory exists
            if not dir_path.exists():
                raise FileNotFoundError(f"Directory not found: {dir_path}")

            if not dir_path.is_dir():
                raise ValueError(f"Not a directory: {dir_path}")

            # List files
            resources = []
            for item in dir_path.iterdir():
                uri = f"file://{item}"

                # Detect MIME type
                mime_type, _ = mimetypes.guess_type(str(item))
                if item.is_dir():
                    mime_type = "text/directory"

                resources.append({
                    "uri": uri,
                    "name": item.name,
                    "description": f"{item.name} ({'directory' if item.is_dir() else 'file'})",
                    "mimeType": mime_type
                })

            return sorted(resources, key=lambda x: x["name"])

        except Exception as e:
            logger.error(f"Error listing resources in {path}: {e}", exc_info=True)
            raise

    async def stream_resource(self, uri: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """
        Stream a file system resource

        Args:
            uri: Resource URI
            chunk_size: Size of chunks to yield

        Yields:
            Chunks of file content
        """
        try:
            # Parse URI
            if uri.startswith("file://"):
                file_path = Path(uri[7:])
            else:
                file_path = self.base_path / uri

            file_path = file_path.resolve()

            # Security check
            try:
                file_path.relative_to(self.base_path.resolve())
            except ValueError:
                raise ValueError(f"Access denied: path outside base directory")

            # Check if file exists
            if not file_path.exists() or not file_path.is_file():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Stream file
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        except Exception as e:
            logger.error(f"Error streaming resource {uri}: {e}", exc_info=True)
            raise


class GitResourceProvider:
    """
    Provider for Git-related resources
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize Git resource provider

        Args:
            repo_path: Path to Git repository
        """
        self.repo_path = repo_path or Path.cwd()

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a Git resource

        Args:
            uri: Resource URI (git://resource-name or git:resource-name)

        Returns:
            Resource contents
        """
        try:
            # Parse resource type
            if uri.startswith("git://"):
                resource_name = uri[6:]
            elif uri.startswith("git:"):
                resource_name = uri[5:]
            else:
                raise ValueError(f"Invalid Git URI: {uri}")

            # Handle different resource types
            if resource_name == "status":
                return await self._get_git_status()
            elif resource_name == "log":
                return await self._get_git_log()
            elif resource_name == "diff":
                return await self._get_git_diff()
            elif resource_name.startswith("branch/"):
                return await self._get_git_branch_info(resource_name[7:])
            else:
                raise ValueError(f"Unknown Git resource: {resource_name}")

        except Exception as e:
            logger.error(f"Error reading Git resource {uri}: {e}", exc_info=True)
            raise

    async def _get_git_status(self) -> Dict[str, Any]:
        """Get Git status"""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git status failed: {result.stderr}")

            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            files = [
                {
                    "status": line[:2],
                    "path": line[3:]
                }
                for line in lines
            ]

            return {
                "uri": "git://status",
                "mimeType": "application/json",
                "text": str(files)
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Git status timed out")
        except FileNotFoundError:
            raise RuntimeError("Git not found")

    async def _get_git_log(self) -> Dict[str, Any]:
        """Get Git log"""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git log failed: {result.stderr}")

            return {
                "uri": "git://log",
                "mimeType": "text/plain",
                "text": result.stdout
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Git log timed out")
        except FileNotFoundError:
            raise RuntimeError("Git not found")

    async def _get_git_diff(self) -> Dict[str, Any]:
        """Get Git diff"""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--color=never"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git diff failed: {result.stderr}")

            return {
                "uri": "git://diff",
                "mimeType": "text/plain",
                "text": result.stdout
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Git diff timed out")
        except FileNotFoundError:
            raise RuntimeError("Git not found")

    async def _get_git_branch_info(self, branch_name: str) -> Dict[str, Any]:
        """Get Git branch information"""
        import subprocess

        try:
            # Get branch info
            result = subprocess.run(
                ["git", "show-branch", branch_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git show-branch failed: {result.stderr}")

            return {
                "uri": f"git://branch/{branch_name}",
                "mimeType": "text/plain",
                "text": result.stdout
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Git branch info timed out")
        except FileNotFoundError:
            raise RuntimeError("Git not found")


class ResourceCache:
    """
    Cache for resource contents
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        """
        Initialize resource cache

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries in cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def get(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Get cached resource

        Args:
            uri: Resource URI

        Returns:
            Cached resource or None if not found/expired
        """
        if uri not in self._cache:
            return None

        entry = self._cache[uri]

        # Check if expired
        if (datetime.now() - entry["timestamp"]).total_seconds() > self.ttl_seconds:
            del self._cache[uri]
            return None

        return entry["data"]

    async def set(self, uri: str, data: Dict[str, Any]) -> None:
        """
        Cache a resource

        Args:
            uri: Resource URI
            data: Resource data
        """
        # Evict oldest entry if cache is full
        if len(self._cache) >= self.max_size and uri not in self._cache:
            oldest_uri = min(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            del self._cache[oldest_uri]

        # Store entry
        self._cache[uri] = {
            "data": data,
            "timestamp": datetime.now()
        }

    async def invalidate(self, uri: str) -> None:
        """
        Invalidate a cached resource

        Args:
            uri: Resource URI
        """
        if uri in self._cache:
            del self._cache[uri]

    async def clear(self) -> None:
        """Clear all cached resources"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Cache statistics
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "entries": [
                {
                    "uri": uri,
                    "age_seconds": (datetime.now() - entry["timestamp"]).total_seconds()
                }
                for uri, entry in self._cache.items()
            ]
        }


class MCPResourceManager:
    """
    Manager for MCP resource operations

    Coordinates multiple resource providers with caching
    """

    def __init__(self):
        """Initialize resource manager"""
        self.providers = {
            "file": FileSystemResourceProvider(),
            "git": GitResourceProvider(),
        }
        self.cache = ResourceCache()

    def register_provider(self, scheme: str, provider) -> None:
        """
        Register a resource provider

        Args:
            scheme: URI scheme (e.g., "file", "git")
            provider: Resource provider instance
        """
        self.providers[scheme] = provider
        logger.info(f"Registered resource provider: {scheme}")

    async def read_resource(self, uri: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Read a resource

        Args:
            uri: Resource URI
            use_cache: Whether to use cache

        Returns:
            Resource contents
        """
        # Check cache first
        if use_cache:
            cached = await self.cache.get(uri)
            if cached:
                logger.debug(f"Cache hit for {uri}")
                return cached

        # Parse URI scheme
        if "://" in uri:
            scheme, path = uri.split("://", 1)
        else:
            scheme = "file"
            path = uri

        # Get provider
        provider = self.providers.get(scheme)
        if not provider:
            raise ValueError(f"No provider for scheme: {scheme}")

        # Read resource
        data = await provider.read_resource(uri)

        # Cache result
        if use_cache:
            await self.cache.set(uri, data)

        return data

    async def list_resources(self, scheme: str = "file", path: str = "") -> List[Dict[str, Any]]:
        """
        List resources

        Args:
            scheme: URI scheme
            path: Path within scheme

        Returns:
            List of resource definitions
        """
        provider = self.providers.get(scheme)
        if not provider:
            raise ValueError(f"No provider for scheme: {scheme}")

        if hasattr(provider, 'list_resources'):
            return await provider.list_resources(path)
        else:
            raise ValueError(f"Provider {scheme} does not support listing")

    async def stream_resource(self, uri: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """
        Stream a resource

        Args:
            uri: Resource URI
            chunk_size: Size of chunks

        Yields:
            Chunks of resource content
        """
        # Parse URI scheme
        if "://" in uri:
            scheme, path = uri.split("://", 1)
        else:
            scheme = "file"
            path = uri

        # Get provider
        provider = self.providers.get(scheme)
        if not provider:
            raise ValueError(f"No provider for scheme: {scheme}")

        if hasattr(provider, 'stream_resource'):
            async for chunk in provider.stream_resource(uri, chunk_size):
                yield chunk
        else:
            # Fallback to reading entire resource
            data = await self.read_resource(uri)
            if "text" in data:
                yield data["text"].encode("utf-8")
            elif "blob" in data:
                import base64
                yield base64.b64decode(data["blob"])

    async def invalidate_cache(self, uri: Optional[str] = None) -> None:
        """
        Invalidate cache

        Args:
            uri: Specific URI to invalidate, or None to clear all
        """
        if uri:
            await self.cache.invalidate(uri)
        else:
            await self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Cache statistics
        """
        return self.cache.get_stats()
