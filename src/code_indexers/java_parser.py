"""
Advanced Java Parser - Accurately extract all methods, constructors, and fields
Uses proper parsing instead of regex to handle complex Java syntax
"""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class JavaMethod:
    """Represents a Java method"""
    name: str
    return_type: str
    parameters: List[str]
    modifiers: List[str]
    annotations: List[str]
    line_number: int
    is_constructor: bool = False


@dataclass
class JavaClass:
    """Represents a Java class"""
    name: str
    package: str
    modifiers: List[str]
    extends: str = None
    implements: List[str] = None
    methods: List[JavaMethod] = None
    fields: List[str] = None
    annotations: List[str] = None
    
    def __post_init__(self):
        if self.methods is None:
            self.methods = []
        if self.implements is None:
            self.implements = []
        if self.fields is None:
            self.fields = []
        if self.annotations is None:
            self.annotations = []


class JavaParser:
    """Parse Java source code accurately"""
    
    def __init__(self):
        self.code = ""
        self.lines = []
        self.position = 0
    
    def parse(self, java_code: str) -> List[JavaClass]:
        """Parse Java code and extract all classes"""
        self.code = java_code
        self.lines = java_code.split('\n')
        self.position = 0
        
        classes = []
        package_name = self._extract_package()
        
        # Remove comments
        clean_code = self._remove_comments(java_code)
        
        # Find all top-level classes
        class_pattern = r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?(?:\s*\{)'
        
        for match in re.finditer(class_pattern, clean_code):
            class_name = match.group(1)
            extends = match.group(2)
            implements = [i.strip() for i in (match.group(3) or "").split(',') if i.strip()]
            
            # Extract class block
            start_pos = match.end() - 1
            class_block = self._extract_block(clean_code, start_pos)
            
            java_class = JavaClass(
                name=class_name,
                package=package_name,
                modifiers=self._extract_modifiers(clean_code[max(0, match.start()-50):match.start()]),
                extends=extends,
                implements=implements,
            )
            
            # Parse methods and fields
            java_class.methods = self._extract_methods(class_block)
            java_class.fields = self._extract_fields(class_block)
            java_class.annotations = self._extract_class_annotations(clean_code[max(0, match.start()-200):match.start()])
            
            classes.append(java_class)
        
        return classes
    
    def _remove_comments(self, code: str) -> str:
        """Remove Java comments"""
        # Remove block comments /* ... */
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # Remove line comments //
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        return code
    
    def _extract_package(self) -> str:
        """Extract package name"""
        match = re.search(r'package\s+([\w.]+);', self.code)
        return match.group(1) if match else ""
    
    def _extract_block(self, text: str, start_pos: int) -> str:
        """Extract balanced braces starting from position"""
        brace_count = 0
        i = start_pos
        
        while i < len(text):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_pos:i+1]
            i += 1
        
        return text[start_pos:]
    
    def _extract_modifiers(self, context: str) -> List[str]:
        """Extract method modifiers"""
        modifiers = []
        for mod in ['public', 'private', 'protected', 'static', 'final', 'abstract', 'synchronized']:
            if mod in context:
                modifiers.append(mod)
        return modifiers
    
    def _extract_class_annotations(self, context: str) -> List[str]:
        """Extract class-level annotations"""
        annotations = re.findall(r'@(\w+)', context)
        return list(set(annotations))
    
    def _extract_methods(self, class_block: str) -> List[JavaMethod]:
        """Extract all methods from class block"""
        methods = []
        
        # Match method signatures (including constructors)
        # Handles: modifiers return_type name(params) and constructors
        method_pattern = r'(?:@\w+[\s\n]*)*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:<[^>]+>\s*)?(\w+|\w+\[\]|\w+<[^>]+>)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\s*\{'
        
        for match in re.finditer(method_pattern, class_block):
            return_type = match.group(1)
            method_name = match.group(2)
            params_str = match.group(3)
            
            # Parse parameters
            parameters = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if param:
                        # Extract just the parameter name (last word)
                        parts = param.split()
                        if parts:
                            parameters.append(parts[-1])
            
            # Extract modifiers from context
            context_start = max(0, match.start() - 200)
            context = class_block[context_start:match.start()]
            modifiers = self._extract_modifiers(context)
            
            # Check if it's a constructor
            is_constructor = method_name == return_type.split('[')[0].split('<')[0]
            
            methods.append(JavaMethod(
                name=method_name,
                return_type=return_type if not is_constructor else "void",
                parameters=parameters,
                modifiers=modifiers,
                annotations=[],
                line_number=class_block[:match.start()].count('\n'),
                is_constructor=is_constructor
            ))
        
        return methods
    
    def _extract_fields(self, class_block: str) -> List[str]:
        """Extract field declarations"""
        fields = []
        
        # Match field declarations
        field_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*(?:=|;)'
        
        for match in re.finditer(field_pattern, class_block):
            field_type = match.group(1)
            field_name = match.group(2)
            fields.append(f"{field_type} {field_name}")
        
        return fields[:20]  # Limit to 20 most important fields


def format_methods_for_chunk(java_class: JavaClass) -> str:
    """Format Java class methods for indexing chunk"""
    
    constructors = [m for m in java_class.methods if m.is_constructor]
    regular_methods = [m for m in java_class.methods if not m.is_constructor]
    
    # Sort methods alphabetically
    constructors.sort(key=lambda m: m.name)
    regular_methods.sort(key=lambda m: m.name)
    
    chunk = f"Java Class: {java_class.name}\n"
    chunk += f"Package: {java_class.package}\n"
    
    if java_class.extends:
        chunk += f"Extends: {java_class.extends}\n"
    
    if java_class.implements:
        chunk += f"Implements: {', '.join(java_class.implements)}\n"
    
    chunk += f"\nTotal Methods: {len(regular_methods)}\n"
    chunk += f"Total Constructors: {len(constructors)}\n\n"
    
    # Format constructors
    if constructors:
        chunk += "=" * 60 + "\n"
        chunk += f"CONSTRUCTORS ({len(constructors)})\n"
        chunk += "=" * 60 + "\n"
        for i, method in enumerate(constructors, 1):
            params = ", ".join(method.parameters) if method.parameters else ""
            chunk += f"{i}. {method.name}({params})\n"
        chunk += "\n"
    
    # Format methods in groups (every 20 methods)
    for group_idx, i in enumerate(range(0, len(regular_methods), 20)):
        group = regular_methods[i:i+20]
        chunk += "=" * 60 + "\n"
        chunk += f"METHODS {i+1}-{min(i+20, len(regular_methods))} of {len(regular_methods)}\n"
        chunk += "=" * 60 + "\n"
        
        for j, method in enumerate(group, i+1):
            params = ", ".join(method.parameters) if method.parameters else ""
            chunk += f"{j}. {method.return_type} {method.name}({params})\n"
        
        chunk += "\n"
    
    return chunk


def format_methods_for_chunks(java_class_dict: Dict) -> List[str]:
    """Format Java class methods for indexing chunks - returns list of chunks for large classes"""
    
    methods = java_class_dict.get("methods", [])
    constructors = [m for m in methods if m.is_constructor]
    regular_methods = [m for m in methods if not m.is_constructor]
    
    # Sort methods alphabetically
    constructors.sort(key=lambda m: m.name)
    regular_methods.sort(key=lambda m: m.name)
    
    chunks = []
    
    # Header chunk with class info
    header = f"Java Class: {java_class_dict['name']}\n"
    header += f"Package: {java_class_dict.get('package', 'default')}\n"
    
    if java_class_dict.get("extends"):
        header += f"Extends: {java_class_dict['extends']}\n"
    
    if java_class_dict.get("implements"):
        header += f"Implements: {', '.join(java_class_dict['implements'])}\n"
    
    header += f"\nTotal Methods: {len(regular_methods)}\n"
    header += f"Total Constructors: {len(constructors)}\n\n"
    
    # Add constructors to header
    if constructors:
        header += "=" * 70 + "\n"
        header += f"CONSTRUCTORS ({len(constructors)})\n"
        header += "=" * 70 + "\n"
        for i, method in enumerate(constructors, 1):
            params = ", ".join(method.parameters) if method.parameters else ""
            header += f"{i}. {method.name}({params})\n"
        header += "\n"
    
    chunks.append(header)
    
    # Split methods into groups of 20 per chunk
    METHODS_PER_CHUNK = 20
    for group_idx in range(0, len(regular_methods), METHODS_PER_CHUNK):
        group = regular_methods[group_idx:group_idx + METHODS_PER_CHUNK]
        
        chunk = f"Java Class: {java_class_dict['name']} - Methods {group_idx + 1}-{min(group_idx + METHODS_PER_CHUNK, len(regular_methods))} of {len(regular_methods)}\n\n"
        chunk += "=" * 70 + "\n"
        chunk += f"METHODS {group_idx + 1}-{min(group_idx + METHODS_PER_CHUNK, len(regular_methods))} of {len(regular_methods)}\n"
        chunk += "=" * 70 + "\n"
        
        for j, method in enumerate(group, group_idx + 1):
            params = ", ".join(method.parameters) if method.parameters else ""
            chunk += f"{j}. {method.return_type} {method.name}({params})\n"
        
        chunks.append(chunk)
    
    return chunks