"""
Enhanced Code Indexer - Semantic extraction for Java, XML, and other languages
Extracts functions, classes, methods, annotations, and structure
"""

import ast
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.documents import Document
from code_indexers.java_parser import JavaParser, format_methods_for_chunks


class EnhancedCodeIndexer:
    """Enhanced code indexing with semantic extraction"""
    
    def extract_code_structure(self, code: str, file_path: str) -> Dict[str, Any]:
        """Extract semantic structure based on file type"""
        language = Path(file_path).suffix.lstrip('.')
        
        if language == "java":
            return self._extract_java_structure(code, file_path)
        elif language == "xml":
            return self._extract_xml_structure(code, file_path)
        elif language == "py":
            return self._extract_python_structure(code, file_path)
        elif language in ["js", "ts", "jsx", "tsx"]:
            return self._extract_js_structure(code, file_path)
        else:
            return self._extract_generic_structure(code, file_path)
    
    def _extract_java_structure(self, code: str, file_path: str) -> Dict[str, Any]:
        """Extract Java structure using proper parser"""
        
        try:
            parser = JavaParser()
            classes = parser.parse(code)
            
            structure = {
                "file_path": file_path,
                "package": classes[0].package if classes else None,
                "imports": self._extract_imports(code),
                "classes": [],
                "annotations": [],
            }
            
            for java_class in classes:
                class_info = {
                    "name": java_class.name,
                    "package": java_class.package,
                    "extends": java_class.extends,
                    "implements": java_class.implements,
                    "methods": java_class.methods,
                    "method_count": len([m for m in java_class.methods if not m.is_constructor]),
                    "constructor_count": len([m for m in java_class.methods if m.is_constructor]),
                }
                structure["classes"].append(class_info)
            
            return structure
        
        except Exception as e:
            print(f"⚠️ Error parsing Java in {file_path}: {e}")
            return {
                "file_path": file_path,
                "package": None,
                "imports": [],
                "classes": [],
                "error": str(e)
            }

    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements"""
        imports = re.findall(r'import\s+(?:static\s+)?([^\s;]+);', code)
        return imports[:20]
    
    def _extract_xml_structure(self, code: str, file_path: str) -> Dict[str, Any]:
        """Extract XML structure, elements, attributes"""
        structure = {
            "file_path": file_path,
            "root_element": None,
            "elements": [],
            "attributes": [],
            "namespaces": [],
        }
        
        try:
            root = ET.fromstring(code)
            
            # Get root element
            structure["root_element"] = root.tag
            
            # Extract namespaces
            namespaces = set()
            for elem in root.iter():
                if '}' in elem.tag:
                    ns = elem.tag.split('}')[0][1:]
                    namespaces.add(ns)
            structure["namespaces"] = list(namespaces)
            
            # Extract elements and attributes
            element_counts = {}
            attribute_keys = set()
            
            for elem in root.iter():
                # Count elements
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                element_counts[tag] = element_counts.get(tag, 0) + 1
                
                # Collect attributes
                for attr_key in elem.attrib.keys():
                    attribute_keys.add(attr_key)
            
            # Store element info (limit to 20)
            structure["elements"] = [
                {"name": name, "count": count}
                for name, count in sorted(element_counts.items(), 
                                         key=lambda x: x[1], reverse=True)[:20]
            ]
            
            structure["attributes"] = list(attribute_keys)[:20]
            
            # Extract text content and structure
            structure["sample_structure"] = self._get_xml_sample(root)
        
        except Exception as e:
            print(f"Error parsing XML in {file_path}: {e}")
        
        return structure
    
    def _get_xml_sample(self, elem, depth=0, max_depth=3):
        """Get simplified XML structure"""
        if depth > max_depth:
            return None
        
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        result = {"tag": tag}
        
        if elem.attrib:
            result["attrs"] = dict(list(elem.attrib.items())[:3])
        
        if elem.text and elem.text.strip():
            result["text"] = elem.text.strip()[:100]
        
        children = {}
        for child in elem:
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if child_tag not in children:
                children[child_tag] = self._get_xml_sample(child, depth+1, max_depth)
        
        if children:
            result["children"] = children
        
        return result
    
    def _extract_python_structure(self, code: str, file_path: str) -> Dict[str, Any]:
        """Extract Python AST information"""
        structure = {
            "file_path": file_path,
            "functions": [],
            "classes": [],
            "imports": [],
        }
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    structure["functions"].append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node),
                    })
                
                elif isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    structure["classes"].append({
                        "name": node.name,
                        "methods": methods,
                        "docstring": ast.get_docstring(node),
                    })
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        structure["imports"].append(alias.name)
        
        except Exception as e:
            print(f"Error parsing Python in {file_path}: {e}")
        
        return structure
    
    def _extract_js_structure(self, code: str, file_path: str) -> Dict[str, Any]:
        """Extract JavaScript/TypeScript structure"""
        structure = {
            "file_path": file_path,
            "functions": [],
            "classes": [],
            "exports": [],
        }
        
        # Extract function declarations
        func_pattern = r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(func_pattern, code):
            structure["functions"].append({
                "name": match.group(1),
                "args": match.group(2).split(','),
            })
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, code):
            structure["classes"].append({
                "name": match.group(1),
                "extends": match.group(2),
            })
        
        # Extract exports
        export_pattern = r'export\s+(?:default\s+)?(?:const|function|class)?\s*(\w+)'
        for match in re.finditer(export_pattern, code):
            structure["exports"].append(match.group(1))
        
        return structure
    
    def _extract_generic_structure(self, code: str, file_path: str) -> Dict[str, Any]:
        """Generic extraction for other languages"""
        structure = {
            "file_path": file_path,
            "estimated_functions": len(re.findall(r'def |function |func ', code)),
            "estimated_classes": len(re.findall(r'class ', code)),
        }
        return structure
    
    def create_enhanced_chunks(self, file_path: str, code: str) -> List[Document]:
        """Create chunks with semantic context"""
        language = Path(file_path).suffix.lstrip('.')
        structure = self.extract_code_structure(code, file_path)
        
        chunks = []
        
        # 1. Create semantic summary chunk
        summary = self._create_summary(file_path, structure, language)
        if summary:
            metadata = {
                'source': file_path,
                'language': language,
                'type': 'semantic_summary',
                'structure_type': language,
            }
            doc = Document(page_content=summary, metadata=metadata)
            chunks.append(doc)
        
        # 2. Create element-level chunks (Java classes, XML elements, etc.)
        element_chunks = self._create_element_chunks(file_path, structure, language, code)
        chunks.extend(element_chunks)
        
        # 3. Create code chunks
        code_chunks = self._create_code_chunks(code, file_path, language)
        chunks.extend(code_chunks)
        
        return chunks
    
    def _create_summary(self, file_path: str, structure: Dict, language: str) -> str:
        """Create file summary"""
        summary = f"File: {file_path}\n"
        summary += f"Language: {language}\n\n"
        
        if language == "java":
            if structure.get("package"):
                summary += f"Package: {structure['package']}\n"
            if structure.get("imports"):
                summary += f"Imports: {', '.join(structure['imports'][:5])}\n"
            if structure.get("classes"):
                class_names = [c["name"] for c in structure["classes"]]
                summary += f"Classes: {', '.join(class_names)}\n"
            if structure.get("interfaces"):
                iface_names = [i["name"] for i in structure["interfaces"]]
                summary += f"Interfaces: {', '.join(iface_names)}\n"
            if structure.get("annotations"):
                summary += f"Annotations used: {', '.join(structure['annotations'][:5])}\n"
        
        elif language == "xml":
            if structure.get("root_element"):
                summary += f"Root element: <{structure['root_element']}>\n"
            if structure.get("namespaces"):
                summary += f"Namespaces: {', '.join(structure['namespaces'])}\n"
            if structure.get("elements"):
                elem_names = [e["name"] for e in structure["elements"][:5]]
                summary += f"Main elements: {', '.join(elem_names)}\n"
            if structure.get("attributes"):
                summary += f"Attributes used: {', '.join(structure['attributes'][:5])}\n"
        
        elif language == "py":
            if structure.get("functions"):
                func_names = [f["name"] for f in structure["functions"][:5]]
                summary += f"Functions: {', '.join(func_names)}\n"
            if structure.get("classes"):
                class_names = [c["name"] for c in structure["classes"][:5]]
                summary += f"Classes: {', '.join(class_names)}\n"
        
        return summary
    
    def _create_element_chunks(self, file_path: str, structure: Dict, language: str, code: str) -> List[Document]:
        """Create focused chunks for classes"""
        chunks = []
        
        if language == "java":
            for cls_info in structure.get("classes", []):
                try:
                    # Create comprehensive method list chunks (multiple chunks for large classes)
                    methods = cls_info.get("methods", [])
                    if methods:
                        # Format all methods for this class - returns list of chunks
                        method_chunks = format_methods_for_chunks(cls_info)
                        
                        for chunk_idx, chunk_content in enumerate(method_chunks):
                            metadata = {
                                'source': file_path,
                                'language': language,
                                'type': 'java_class_methods',
                                'class_name': cls_info['name'],
                                'method_count': cls_info.get('method_count', 0),
                                'constructor_count': cls_info.get('constructor_count', 0),
                                'chunk_index': chunk_idx,
                            }
                            chunks.append(Document(page_content=chunk_content, metadata=metadata))
                    
                    # Also create basic class info chunk
                    chunk_content = f"Java Class: {cls_info['name']}\n"
                    chunk_content += f"Package: {cls_info.get('package', 'default')}\n"
                    if cls_info.get("extends"):
                        chunk_content += f"Extends: {cls_info['extends']}\n"
                    if cls_info.get("implements"):
                        chunk_content += f"Implements: {', '.join(cls_info['implements'])}\n"
                    chunk_content += f"\nMethods: {cls_info.get('method_count', 0)}\n"
                    chunk_content += f"Constructors: {cls_info.get('constructor_count', 0)}\n"
                    
                    metadata = {
                        'source': file_path,
                        'language': language,
                        'type': 'java_class_info',
                        'class_name': cls_info['name'],
                    }
                    chunks.append(Document(page_content=chunk_content, metadata=metadata))
                
                except Exception as e:
                    print(f"⚠️ Warning: Could not parse class {cls_info.get('name', 'unknown')} in {file_path}: {e}")
                    continue
        
        elif language == "xml":
            # XML element chunks
            for elem in structure.get("elements", [])[:10]:
                chunk_content = f"XML Element: <{elem['name']}>\n"
                chunk_content += f"Occurrences: {elem['count']}\n"
                chunk_content += f"File: {file_path}\n"
                
                if structure.get("namespaces"):
                    chunk_content += f"File namespaces: {', '.join(structure['namespaces'])}\n"
                
                metadata = {
                    'source': file_path,
                    'language': language,
                    'type': 'xml_element',
                    'element_name': elem['name'],
                    'element_count': elem['count'],
                }
                chunks.append(Document(page_content=chunk_content, metadata=metadata))
        
        return chunks
    
    def _create_code_chunks(self, code: str, file_path: str, language: str) -> List[Document]:
        """Create regular code chunks"""
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        # Adjust chunk size based on language
        chunk_size = 1500 if language in ["java", "xml"] else 1200
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=250,
            separators=["\n\n", "\nclass ", "\npublic ", "\n}", "\n", "."],
        )
        
        chunks = []
        for chunk in splitter.split_text(code):
            metadata = {
                'source': file_path,
                'language': language,
                'type': 'code_chunk',
            }
            chunks.append(Document(page_content=chunk, metadata=metadata))
        
        return chunks