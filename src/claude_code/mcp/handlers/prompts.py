"""
MCP Prompt Handlers
Handles prompt templates and variable substitution
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptTemplate:
    """
    Prompt template with variable substitution
    """

    def __init__(self, name: str, description: str, template: str, arguments: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize prompt template

        Args:
            name: Template name
            description: Template description
            template: Template string with {{variable}} placeholders
            arguments: List of argument definitions
        """
        self.name = name
        self.description = description
        self.template = template
        self.arguments = arguments or []

        # Extract variables from template
        self.variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        """
        Extract variable names from template

        Returns:
            List of variable names
        """
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, self.template)
        return list(set(matches))

    def render(self, variables: Dict[str, Any]) -> str:
        """
        Render template with variable substitution

        Args:
            variables: Variable values

        Returns:
            Rendered template string

        Raises:
            ValueError: If required variable is missing
        """
        # Check for missing required variables
        required_vars = [arg["name"] for arg in self.arguments if arg.get("required", False)]
        for var in required_vars:
            if var not in variables:
                raise ValueError(f"Missing required variable: {var}")

        # Substitute variables
        result = self.template
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            result = result.replace(placeholder, str(var_value))

        return result

    def validate_arguments(self, arguments: Dict[str, Any]) -> List[str]:
        """
        Validate provided arguments

        Args:
            arguments: Arguments to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for arg_def in self.arguments:
            arg_name = arg_def["name"]
            is_required = arg_def.get("required", False)

            if is_required and arg_name not in arguments:
                errors.append(f"Missing required argument: {arg_name}")

        return errors


class PromptTemplateManager:
    """
    Manager for prompt templates
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize prompt template manager

        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir or Path.home() / ".claude" / "templates"
        self.templates: Dict[str, PromptTemplate] = {}

        # Load built-in templates
        self._load_builtin_templates()

        # Load custom templates if directory exists
        if self.templates_dir.exists():
            self._load_custom_templates()

    def _load_builtin_templates(self) -> None:
        """Load built-in prompt templates"""
        builtin_templates = [
            {
                "name": "code-review",
                "description": "Review code for issues and improvements",
                "template": """Please review the following code and provide feedback:

```{{language}}
{{code}}
```

Focus on:
- Code quality and best practices
- Potential bugs or issues
- Performance considerations
- Security concerns
- Suggestions for improvement

Provide specific, actionable feedback.""",
                "arguments": [
                    {"name": "code", "description": "Code to review", "required": True},
                    {"name": "language", "description": "Programming language", "required": False}
                ]
            },
            {
                "name": "explain-code",
                "description": "Explain what code does",
                "template": """Please explain the following {{language}} code:

```{{language}}
{{code}}
```

Provide:
- High-level overview of what the code does
- Line-by-line or section-by-section explanation
- Key concepts and patterns used
- Any assumptions or dependencies""",
                "arguments": [
                    {"name": "code", "description": "Code to explain", "required": True},
                    {"name": "language", "description": "Programming language", "required": False}
                ]
            },
            {
                "name": "generate-tests",
                "description": "Generate unit tests for code",
                "template": """Generate comprehensive unit tests for the following {{language}} code:

```{{language}}
{{code}}
```

Requirements:
- Use appropriate testing framework for {{language}}
- Test both happy paths and edge cases
- Include test documentation
- Ensure tests are independent and repeatable
- Mock external dependencies as needed""",
                "arguments": [
                    {"name": "code", "description": "Code to test", "required": True},
                    {"name": "language", "description": "Programming language", "required": False}
                ]
            },
            {
                "name": "refactor-code",
                "description": "Refactor code for better structure",
                "template": """Refactor the following {{language}} code to improve:

```{{language}}
{{code}}
```

Refactoring goals:
- Improve code organization and readability
- Follow SOLID principles
- Reduce complexity
- Maintain existing functionality
- Add appropriate error handling

Provide:
- Refactored code
- Explanation of changes made
- Benefits of the refactoring""",
                "arguments": [
                    {"name": "code", "description": "Code to refactor", "required": True},
                    {"name": "language", "description": "Programming language", "required": False}
                ]
            },
            {
                "name": "debug-code",
                "description": "Help debug code with issues",
                "template": """Help debug the following {{language}} code:

```{{language}}
{{code}}
```

{{#if error}}
Error encountered:
```
{{error}}
```
{{/if}}

Please:
1. Identify the likely cause of the issue
2. Explain why it's happening
3. Provide a solution
4. Suggest how to prevent similar issues""",
                "arguments": [
                    {"name": "code", "description": "Code with issues", "required": True},
                    {"name": "language", "description": "Programming language", "required": False},
                    {"name": "error", "description": "Error message or description", "required": False}
                ]
            },
            {
                "name": "write-documentation",
                "description": "Generate documentation for code",
                "template": """Generate comprehensive documentation for the following {{language}} code:

```{{language}}
{{code}}
```

Include:
- Module/function/class overview
- Parameter descriptions with types
- Return value documentation
- Usage examples
- Edge cases and error conditions
- Dependencies and requirements
- Any relevant notes or warnings""",
                "arguments": [
                    {"name": "code", "description": "Code to document", "required": True},
                    {"name": "language", "description": "Programming language", "required": False}
                ]
            },
            {
                "name": "optimize-code",
                "description": "Optimize code for better performance",
                "template": """Optimize the following {{language}} code for better performance:

```{{language}}
{{code}}
```

{{#if constraints}}
Performance constraints:
- Target: {{constraints}}
- Environment: {{environment}}
{{/if}}

Provide:
- Optimized code
- Performance analysis
- Benchmark comparison (if applicable)
- Trade-offs considered
- Additional optimization suggestions""",
                "arguments": [
                    {"name": "code", "description": "Code to optimize", "required": True},
                    {"name": "language", "description": "Programming language", "required": False},
                    {"name": "constraints", "description": "Performance constraints or goals", "required": False},
                    {"name": "environment", "description": "Execution environment", "required": False}
                ]
            }
        ]

        for template_data in builtin_templates:
            template = PromptTemplate(
                name=template_data["name"],
                description=template_data["description"],
                template=template_data["template"],
                arguments=template_data["arguments"]
            )
            self.templates[template.name] = template

        logger.info(f"Loaded {len(builtin_templates)} built-in templates")

    def _load_custom_templates(self) -> None:
        """Load custom prompt templates from directory"""
        if not self.templates_dir.exists():
            return

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)

                template = PromptTemplate(
                    name=template_data["name"],
                    description=template_data.get("description", ""),
                    template=template_data["template"],
                    arguments=template_data.get("arguments", [])
                )
                self.templates[template.name] = template
                logger.info(f"Loaded custom template: {template.name}")

            except Exception as e:
                logger.error(f"Error loading template from {template_file}: {e}")

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get a prompt template by name

        Args:
            name: Template name

        Returns:
            PromptTemplate or None if not found
        """
        return self.templates.get(name)

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available templates

        Returns:
            List of template information
        """
        return [
            {
                "name": template.name,
                "description": template.description,
                "variables": template.variables,
                "arguments": template.arguments
            }
            for template in self.templates.values()
        ]

    def render_template(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        Render a template with arguments

        Args:
            name: Template name
            arguments: Template arguments

        Returns:
            Rendered template string

        Raises:
            ValueError: If template not found or validation fails
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template not found: {name}")

        # Validate arguments
        errors = template.validate_arguments(arguments)
        if errors:
            raise ValueError(f"Template validation failed: {'; '.join(errors)}")

        return template.render(arguments)

    def add_template(self, template: PromptTemplate) -> None:
        """
        Add a new template

        Args:
            template: Template to add
        """
        self.templates[template.name] = template
        logger.info(f"Added template: {template.name}")

    def remove_template(self, name: str) -> bool:
        """
        Remove a template

        Args:
            name: Template name

        Returns:
            True if removed, False if not found
        """
        if name in self.templates:
            del self.templates[name]
            logger.info(f"Removed template: {name}")
            return True
        return False

    def save_template(self, name: str, file_path: Optional[Path] = None) -> None:
        """
        Save a template to file

        Args:
            name: Template name
            file_path: Optional file path (defaults to templates_dir)
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template not found: {name}")

        if file_path is None:
            file_path = self.templates_dir / f"{name}.json"

        file_path.parent.mkdir(parents=True, exist_ok=True)

        template_data = {
            "name": template.name,
            "description": template.description,
            "template": template.template,
            "arguments": template.arguments
        }

        with open(file_path, 'w') as f:
            json.dump(template_data, f, indent=2)

        logger.info(f"Saved template to {file_path}")


class MCPPromptHandler:
    """
    Handler for MCP prompt operations
    """

    def __init__(self, template_manager: PromptTemplateManager):
        """
        Initialize prompt handler

        Args:
            template_manager: Prompt template manager
        """
        self.template_manager = template_manager

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a rendered prompt

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt message in MCP format
        """
        if arguments is None:
            arguments = {}

        try:
            # Render template
            rendered_text = self.template_manager.render_template(name, arguments)

            # Format as MCP message
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": rendered_text
                        }
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Error getting prompt {name}: {e}", exc_info=True)
            raise

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List available prompts

        Returns:
            List of prompt definitions
        """
        templates = self.template_manager.list_templates()

        return [
            {
                "name": template["name"],
                "description": template["description"],
                "arguments": [
                    {
                        "name": arg["name"],
                        "description": arg.get("description", ""),
                        "required": arg.get("required", False)
                    }
                    for arg in template["arguments"]
                ]
            }
            for template in templates
        ]

    async def validate_prompt_arguments(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate prompt arguments

        Args:
            name: Prompt name
            arguments: Arguments to validate

        Returns:
            Validation result
        """
        template = self.template_manager.get_template(name)
        if not template:
            return {
                "valid": False,
                "errors": [f"Prompt not found: {name}"]
            }

        errors = template.validate_arguments(arguments)

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    async def create_custom_prompt(
        self,
        name: str,
        description: str,
        template: str,
        arguments: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Create a custom prompt

        Args:
            name: Prompt name
            description: Prompt description
            template: Template string
            arguments: Argument definitions
        """
        prompt_template = PromptTemplate(
            name=name,
            description=description,
            template=template,
            arguments=arguments or []
        )

        self.template_manager.add_template(prompt_template)

        # Save to file
        self.template_manager.save_template(name)

    async def delete_prompt(self, name: str) -> bool:
        """
        Delete a custom prompt

        Args:
            name: Prompt name

        Returns:
            True if deleted, False if not found
        """
        removed = self.template_manager.remove_template(name)

        if removed:
            # Delete file if it exists
            file_path = self.template_manager.templates_dir / f"{name}.json"
            if file_path.exists():
                file_path.unlink()

        return removed
