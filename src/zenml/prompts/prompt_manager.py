#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Prompt management utilities for organizing and operating on prompt collections."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from zenml.prompts.prompt import Prompt
from zenml.prompts.prompt_comparison import PromptComparison, compare_prompts


class PromptFilter(BaseModel):
    """Filter criteria for finding prompts."""
    
    # Basic filters
    prompt_type: Optional[str] = None
    task: Optional[str] = None
    domain: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    
    # Tag-based filtering
    tags: Optional[List[str]] = None
    tags_mode: str = Field(default="any", description="'any' or 'all' for tag matching")
    
    # Model compatibility
    compatible_with_model: Optional[str] = None
    
    # Performance criteria
    min_performance: Optional[Dict[str, float]] = None
    max_performance: Optional[Dict[str, float]] = None
    
    # Date range
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Content filters
    contains_text: Optional[str] = None
    min_template_length: Optional[int] = None
    max_template_length: Optional[int] = None
    
    # Complexity
    min_complexity: Optional[float] = None
    max_complexity: Optional[float] = None


class PromptCollection(BaseModel):
    """A collection of related prompts."""
    
    name: str = Field(..., description="Name of the collection")
    description: Optional[str] = Field(None, description="Description of the collection")
    prompts: List[Prompt] = Field(default_factory=list, description="Prompts in the collection")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.now, description="When collection was created")
    
    def add_prompt(self, prompt: Prompt) -> None:
        """Add a prompt to the collection."""
        if prompt not in self.prompts:
            self.prompts.append(prompt)
    
    def remove_prompt(self, prompt_id: str) -> bool:
        """Remove a prompt from the collection by ID."""
        for i, prompt in enumerate(self.prompts):
            if prompt.prompt_id == prompt_id:
                del self.prompts[i]
                return True
        return False
    
    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Get a prompt by ID."""
        for prompt in self.prompts:
            if prompt.prompt_id == prompt_id:
                return prompt
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the collection."""
        if not self.prompts:
            return {
                "total_prompts": 0,
                "tasks": [],
                "domains": [],
                "prompt_types": [],
                "languages": [],
                "avg_complexity": 0.0,
            }
        
        tasks = [p.task for p in self.prompts if p.task]
        domains = [p.domain for p in self.prompts if p.domain]
        prompt_types = [p.prompt_type for p in self.prompts if p.prompt_type]
        languages = [p.language for p in self.prompts if p.language]
        
        complexities = [p.get_complexity_score() for p in self.prompts]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0
        
        return {
            "total_prompts": len(self.prompts),
            "tasks": list(set(tasks)),
            "domains": list(set(domains)),
            "prompt_types": list(set(prompt_types)),
            "languages": list(set(languages)),
            "avg_complexity": avg_complexity,
            "creation_date": self.created_at,
        }


class PromptManager:
    """Manager for prompt collections and operations."""
    
    def __init__(self):
        """Initialize the prompt manager."""
        self.collections: Dict[str, PromptCollection] = {}
        self._prompt_index: Dict[str, str] = {}  # prompt_id -> collection_name
    
    def create_collection(
        self, 
        name: str, 
        description: Optional[str] = None,
        initial_prompts: Optional[List[Prompt]] = None
    ) -> PromptCollection:
        """Create a new prompt collection.
        
        Args:
            name: Name of the collection
            description: Optional description
            initial_prompts: Initial prompts to add
            
        Returns:
            Created PromptCollection
        """
        if name in self.collections:
            raise ValueError(f"Collection '{name}' already exists")
        
        collection = PromptCollection(
            name=name,
            description=description,
            prompts=initial_prompts or []
        )
        
        self.collections[name] = collection
        
        # Update index
        for prompt in collection.prompts:
            self._prompt_index[prompt.prompt_id] = name
        
        return collection
    
    def get_collection(self, name: str) -> Optional[PromptCollection]:
        """Get a collection by name."""
        return self.collections.get(name)
    
    def list_collections(self) -> List[str]:
        """List all collection names."""
        return list(self.collections.keys())
    
    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if name not in self.collections:
            return False
        
        # Remove from index
        collection = self.collections[name]
        for prompt in collection.prompts:
            self._prompt_index.pop(prompt.prompt_id, None)
        
        del self.collections[name]
        return True
    
    def add_prompt_to_collection(
        self, 
        collection_name: str, 
        prompt: Prompt
    ) -> bool:
        """Add a prompt to a collection.
        
        Args:
            collection_name: Name of the collection
            prompt: Prompt to add
            
        Returns:
            True if successful, False if collection doesn't exist
        """
        collection = self.collections.get(collection_name)
        if not collection:
            return False
        
        collection.add_prompt(prompt)
        self._prompt_index[prompt.prompt_id] = collection_name
        return True
    
    def find_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Find a prompt by ID across all collections."""
        collection_name = self._prompt_index.get(prompt_id)
        if not collection_name:
            return None
        
        collection = self.collections.get(collection_name)
        if not collection:
            return None
        
        return collection.get_prompt(prompt_id)
    
    def search_prompts(
        self, 
        filter_criteria: PromptFilter,
        collection_names: Optional[List[str]] = None
    ) -> List[Prompt]:
        """Search for prompts matching filter criteria.
        
        Args:
            filter_criteria: Filter criteria to apply
            collection_names: Optional list of collection names to search in
            
        Returns:
            List of matching prompts
        """
        collections_to_search = collection_names or list(self.collections.keys())
        matching_prompts = []
        
        for collection_name in collections_to_search:
            collection = self.collections.get(collection_name)
            if not collection:
                continue
            
            for prompt in collection.prompts:
                if self._matches_filter(prompt, filter_criteria):
                    matching_prompts.append(prompt)
        
        return matching_prompts
    
    def _matches_filter(self, prompt: Prompt, filter_criteria: PromptFilter) -> bool:
        """Check if a prompt matches the filter criteria."""
        # Basic field matching
        if filter_criteria.prompt_type and prompt.prompt_type != filter_criteria.prompt_type:
            return False
        
        if filter_criteria.task and prompt.task != filter_criteria.task:
            return False
        
        if filter_criteria.domain and prompt.domain != filter_criteria.domain:
            return False
        
        if filter_criteria.author and prompt.author != filter_criteria.author:
            return False
        
        if filter_criteria.language and prompt.language != filter_criteria.language:
            return False
        
        # Tag matching
        if filter_criteria.tags and prompt.tags:
            if filter_criteria.tags_mode == "all":
                if not all(tag in prompt.tags for tag in filter_criteria.tags):
                    return False
            else:  # "any"
                if not any(tag in prompt.tags for tag in filter_criteria.tags):
                    return False
        elif filter_criteria.tags:
            return False
        
        # Model compatibility
        if filter_criteria.compatible_with_model:
            if not prompt.is_compatible_with_model(filter_criteria.compatible_with_model):
                return False
        
        # Performance criteria
        if filter_criteria.min_performance and prompt.performance_metrics:
            for metric, min_val in filter_criteria.min_performance.items():
                if prompt.performance_metrics.get(metric, float('-inf')) < min_val:
                    return False
        
        if filter_criteria.max_performance and prompt.performance_metrics:
            for metric, max_val in filter_criteria.max_performance.items():
                if prompt.performance_metrics.get(metric, float('inf')) > max_val:
                    return False
        
        # Date range
        if filter_criteria.created_after and prompt.created_at:
            if prompt.created_at < filter_criteria.created_after:
                return False
        
        if filter_criteria.created_before and prompt.created_at:
            if prompt.created_at > filter_criteria.created_before:
                return False
        
        # Content filters
        if filter_criteria.contains_text:
            if filter_criteria.contains_text.lower() not in prompt.template.lower():
                return False
        
        if filter_criteria.min_template_length:
            if len(prompt.template) < filter_criteria.min_template_length:
                return False
        
        if filter_criteria.max_template_length:
            if len(prompt.template) > filter_criteria.max_template_length:
                return False
        
        # Complexity
        complexity = prompt.get_complexity_score()
        if filter_criteria.min_complexity and complexity < filter_criteria.min_complexity:
            return False
        
        if filter_criteria.max_complexity and complexity > filter_criteria.max_complexity:
            return False
        
        return True
    
    def get_prompt_variants(self, prompt_id: str) -> List[Prompt]:
        """Get all variants of a prompt (children and siblings).
        
        Args:
            prompt_id: ID of the base prompt
            
        Returns:
            List of variant prompts
        """
        base_prompt = self.find_prompt(prompt_id)
        if not base_prompt:
            return []
        
        variants = []
        
        # Find all prompts across collections
        for collection in self.collections.values():
            for prompt in collection.prompts:
                # Child variants (this prompt is parent)
                if prompt.parent_prompt_id == prompt_id:
                    variants.append(prompt)
                
                # Sibling variants (same parent)
                elif (prompt.parent_prompt_id and 
                      base_prompt.parent_prompt_id and
                      prompt.parent_prompt_id == base_prompt.parent_prompt_id and
                      prompt.prompt_id != prompt_id):
                    variants.append(prompt)
        
        return variants
    
    def compare_prompt_performance(
        self, 
        prompt_ids: List[str],
        metric: str = "accuracy"
    ) -> Dict[str, Any]:
        """Compare performance of multiple prompts.
        
        Args:
            prompt_ids: List of prompt IDs to compare
            metric: Performance metric to compare
            
        Returns:
            Performance comparison data
        """
        prompts = [self.find_prompt(pid) for pid in prompt_ids]
        prompts = [p for p in prompts if p is not None]
        
        if len(prompts) < 2:
            raise ValueError("Need at least 2 prompts for comparison")
        
        performance_data = {}
        
        for prompt in prompts:
            performance_data[prompt.prompt_id] = {
                "prompt_info": {
                    "id": prompt.prompt_id,
                    "description": prompt.description,
                    "version": prompt.version,
                    "task": prompt.task,
                    "domain": prompt.domain,
                },
                "performance": prompt.performance_metrics or {},
                "target_metric": prompt.performance_metrics.get(metric) if prompt.performance_metrics else None
            }
        
        # Find best performer
        valid_performances = [
            (pid, data["target_metric"]) 
            for pid, data in performance_data.items() 
            if data["target_metric"] is not None
        ]
        
        best_performer = None
        if valid_performances:
            best_performer = max(valid_performances, key=lambda x: x[1])[0]
        
        return {
            "metric": metric,
            "prompts": performance_data,
            "best_performer": best_performer,
            "comparison_date": datetime.now(),
        }
    
    def create_prompt_experiment(
        self,
        experiment_name: str,
        base_prompt: Prompt,
        variations: List[Dict[str, Any]],
        collection_name: Optional[str] = None
    ) -> PromptCollection:
        """Create an experiment with prompt variations.
        
        Args:
            experiment_name: Name of the experiment
            base_prompt: Base prompt to create variations from
            variations: List of variation specifications
            collection_name: Optional collection name (defaults to experiment name)
            
        Returns:
            PromptCollection containing the experiment prompts
        """
        collection_name = collection_name or f"experiment_{experiment_name}"
        
        # Create base prompt variant
        experiment_prompts = [base_prompt.clone(
            description=f"{experiment_name} - Base",
            metadata={
                "experiment": experiment_name,
                "variant_type": "base",
                "experiment_created": datetime.now().isoformat()
            }
        )]
        
        # Create variations
        for i, variation in enumerate(variations):
            variant = base_prompt.clone(
                description=f"{experiment_name} - Variant {i+1}",
                metadata={
                    "experiment": experiment_name,
                    "variant_type": f"variant_{i+1}",
                    "experiment_created": datetime.now().isoformat()
                },
                **variation
            )
            experiment_prompts.append(variant)
        
        # Create collection
        return self.create_collection(
            name=collection_name,
            description=f"Prompt experiment: {experiment_name}",
            initial_prompts=experiment_prompts
        )
    
    def export_collection(
        self, 
        collection_name: str, 
        format: str = "json"
    ) -> str:
        """Export a collection to string format.
        
        Args:
            collection_name: Name of collection to export
            format: Export format ("json" or "yaml")
            
        Returns:
            Exported data as string
        """
        collection = self.collections.get(collection_name)
        if not collection:
            raise ValueError(f"Collection '{collection_name}' not found")
        
        export_data = {
            "collection_name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at.isoformat(),
            "metadata": collection.metadata,
            "prompts": [prompt.to_dict() for prompt in collection.prompts]
        }
        
        if format.lower() == "json":
            return json.dumps(export_data, indent=2, default=str)
        elif format.lower() == "yaml":
            import yaml
            return yaml.dump(export_data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_collection(
        self, 
        data: str, 
        format: str = "json",
        overwrite: bool = False
    ) -> PromptCollection:
        """Import a collection from string data.
        
        Args:
            data: Data string to import
            format: Data format ("json" or "yaml")
            overwrite: Whether to overwrite existing collection
            
        Returns:
            Imported PromptCollection
        """
        if format.lower() == "json":
            import_data = json.loads(data)
        elif format.lower() == "yaml":
            import yaml
            import_data = yaml.safe_load(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        collection_name = import_data["collection_name"]
        
        if collection_name in self.collections and not overwrite:
            raise ValueError(f"Collection '{collection_name}' already exists. Use overwrite=True to replace.")
        
        # Convert prompt dicts back to Prompt objects
        prompts = [Prompt.from_dict(prompt_data) for prompt_data in import_data["prompts"]]
        
        # Create or update collection
        if collection_name in self.collections:
            self.delete_collection(collection_name)
        
        collection = PromptCollection(
            name=collection_name,
            description=import_data.get("description"),
            prompts=prompts,
            metadata=import_data.get("metadata", {}),
            created_at=datetime.fromisoformat(import_data["created_at"])
        )
        
        self.collections[collection_name] = collection
        
        # Update index
        for prompt in prompts:
            self._prompt_index[prompt.prompt_id] = collection_name
        
        return collection
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics for the prompt manager."""
        total_prompts = sum(len(collection.prompts) for collection in self.collections.values())
        
        all_prompts = []
        for collection in self.collections.values():
            all_prompts.extend(collection.prompts)
        
        if not all_prompts:
            return {
                "total_collections": len(self.collections),
                "total_prompts": 0,
                "tasks": [],
                "domains": [],
                "languages": [],
                "avg_complexity": 0.0,
            }
        
        tasks = [p.task for p in all_prompts if p.task]
        domains = [p.domain for p in all_prompts if p.domain]
        languages = [p.language for p in all_prompts if p.language]
        
        complexities = [p.get_complexity_score() for p in all_prompts]
        avg_complexity = sum(complexities) / len(complexities)
        
        return {
            "total_collections": len(self.collections),
            "total_prompts": total_prompts,
            "unique_tasks": len(set(tasks)),
            "unique_domains": len(set(domains)),
            "unique_languages": len(set(languages)),
            "avg_complexity": avg_complexity,
            "tasks": list(set(tasks)),
            "domains": list(set(domains)),
            "languages": list(set(languages)),
        }