"""
Grasshopper Tools - Early Integration

This module contains basic Grasshopper tools extracted from the production codebase.
These are the EXACT same functions used in production, just fewer of them.

Tools are automatically registered using the @gh_tool decorator.
"""

import sys
import os
from typing import Dict, Any

# Import bridge_client from MCP directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'MCP'))
from bridge_client import call_bridge_api

# Import the decorator system
try:
    from .tool_registry import gh_tool, bridge_handler
except ImportError:
    # Fallback for direct import
    from tool_registry import gh_tool, bridge_handler

# Get DEBUG_MODE from environment
DEBUG_MODE = False
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env_file = os.path.join(project_root, '.env')

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == 'DEBUG_MODE':
                        DEBUG_MODE = value.strip().lower() == 'true'
                        break
    else:
        DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
except:
    DEBUG_MODE = False

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ensure_file_is_active(file_name: str) -> Dict[str, Any]:
    """
    Helper function to check if a specific Grasshopper file is active.
    For Level 2 (Early Integration), this is a simplified version.

    Args:
        file_name: Name of the .gh file that should be active

    Returns:
        Dict with 'success' boolean and optional 'error' message
    """
    if not file_name:
        return {"success": True}  # No specific file requested, use whatever is active

    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import os

        # Check if requested file is already active
        if Grasshopper.Instances.ActiveCanvas and Grasshopper.Instances.ActiveCanvas.Document:
            active_doc = Grasshopper.Instances.ActiveCanvas.Document
            if active_doc.FilePath:
                active_file_name = os.path.basename(str(active_doc.FilePath))
                if active_file_name.lower() == file_name.lower():
                    return {"success": True}  # Already active

        # File not active - return error asking user to open it
        return {
            "success": False,
            "error": f"File '{file_name}' is not active. Please open the file in Grasshopper first."
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error checking file: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ============================================================================
# GRASSHOPPER TOOLS
# ============================================================================

@gh_tool(
    name="get_active_gh_files",
    description=(
        "Get information about all currently open Grasshopper files. "
        "Returns details about each open document including file paths, "
        "names, and which one is currently active.\n\n"
        "**Returns:**\n"
        "Dictionary containing list of open Grasshopper documents."
    )
)
async def get_active_gh_files() -> Dict[str, Any]:
    """
    Get all currently open Grasshopper files.

    Returns:
        Dict containing information about open files
    """
    return call_bridge_api("/get_active_gh_files", {})

@bridge_handler("/get_active_gh_files")
def handle_get_active_gh_files(data):
    """Bridge handler for getting active .gh files"""
    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import Rhino
        import os

        # Get the Grasshopper plugin
        gh = Rhino.RhinoApp.GetPlugInObject("Grasshopper")
        if not gh:
            return {
                "success": False,
                "error": "Grasshopper plugin not available",
                "open_files": []
            }

        open_files = []
        active_doc_path = None

        # Get the active document path
        if Grasshopper.Instances.ActiveCanvas and Grasshopper.Instances.ActiveCanvas.Document:
            active_doc = Grasshopper.Instances.ActiveCanvas.Document
            if active_doc.FilePath:
                active_doc_path = os.path.normpath(str(active_doc.FilePath)).lower()

        # Iterate through ALL open documents using DocumentServer
        doc_server = Grasshopper.Instances.DocumentServer
        if doc_server:
            for doc in doc_server:
                if doc and hasattr(doc, 'FilePath') and doc.FilePath:
                    file_path = str(doc.FilePath)
                    file_name = os.path.basename(file_path)
                    normalized_path = os.path.normpath(file_path).lower()

                    # Check if this is the active document
                    is_active = (active_doc_path is not None and normalized_path == active_doc_path)

                    open_files.append({
                        "name": file_name,
                        "path": file_path,
                        "is_active": is_active,
                        "is_modified": doc.IsModified if hasattr(doc, 'IsModified') else False,
                        "object_count": doc.ObjectCount if hasattr(doc, 'ObjectCount') else 0
                    })

        if len(open_files) == 0:
            return {
                "success": False,
                "error": "No open Grasshopper documents found",
                "open_files": []
            }

        return {
            "success": True,
            "open_files": open_files,
            "count": len(open_files),
            "message": f"Found {len(open_files)} open Grasshopper document(s)"
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error getting active files: {str(e)}",
            "traceback": traceback.format_exc(),
            "open_files": []
        }

@gh_tool(
    name="list_grasshopper_sliders",
    description=(
        "List all available slider components in a specific Grasshopper file. "
        "This tool will activate the specified file (making it visible to the user), "
        "then scan it to find all number slider components and return their names and current values.\n\n"
        "**Parameters:**\n"
        "- **file_name** (str, required): Name of the .gh file to list sliders from (e.g., 'Primary Truss Generator.gh')\n"
        "\n**Returns:**\n"
        "Dictionary containing list of sliders with their names and current values."
    )
)
async def list_grasshopper_sliders(file_name: str) -> Dict[str, Any]:
    """
    List all slider components in a specific Grasshopper file via HTTP bridge.

    Args:
        file_name: Name of the .gh file to list sliders from

    Returns:
        Dict containing slider information
    """

    request_data = {
        "file_name": file_name
    }

    return call_bridge_api("/list_sliders", request_data)

@bridge_handler("/list_sliders")
def handle_list_sliders(data):
    """Bridge handler for list sliders requests"""
    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import Rhino

        file_name = data.get('file_name', '')

        # Ensure the correct file is active first
        activation_result = ensure_file_is_active(file_name)
        if not activation_result.get("success", False):
            return {
                "success": False,
                "error": activation_result.get("error", "Failed to activate file"),
                "file_name": file_name,
                "sliders": []
            }

        # Get the Grasshopper plugin and document
        gh = Rhino.RhinoApp.GetPlugInObject("Grasshopper")
        if not gh:
            return {
                "success": False,
                "error": "Grasshopper plugin not available",
                "file_name": file_name,
                "sliders": []
            }

        gh_doc = Grasshopper.Instances.ActiveCanvas.Document if Grasshopper.Instances.ActiveCanvas else None
        if not gh_doc:
            return {
                "success": False,
                "error": "No active Grasshopper document found",
                "file_name": file_name,
                "sliders": []
            }

        sliders = []

        for obj in gh_doc.Objects:
            if isinstance(obj, Grasshopper.Kernel.Special.GH_NumberSlider):
                slider_info = {
                    "name": obj.NickName or "Unnamed",
                    "current_value": float(str(obj.Slider.Value)),
                    "min_value": float(str(obj.Slider.Minimum)),
                    "max_value": float(str(obj.Slider.Maximum)),
                    "precision": obj.Slider.DecimalPlaces,
                    "type": obj.Slider.Type.ToString()
                }
                sliders.append(slider_info)

        return {
            "success": True,
            "sliders": sliders,
            "count": len(sliders),
            "message": f"Found {len(sliders)} slider components"
        }

    except ImportError as e:
        return {
            "success": False,
            "error": f"Grasshopper not available: {str(e)}",
            "sliders": []
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error listing sliders: {str(e)}",
            "traceback": traceback.format_exc(),
            "sliders": []
        }

# ============================================================================
# OUR CUSTOM GRASSHOPPER TOOLS
# ============================================================================

@gh_tool(
    name="generate_building_massing",
    description=(
        "Generate a parametric building massing model in Grasshopper from building parameters. "
        "This tool creates a 3D building volume from a footprint polyline, core rectangle, "
        "and height/floor parameters. It will load the BuildingMassingGenerator.gh file and "
        "execute it with the provided parameters to create the massing geometry.\n\n"
        "**Parameters:**\n"
        "- **footprint_points** (list): Array of coordinate dictionaries with 'x' and 'y' keys defining the building footprint\n"
        "- **core_center** (dict): Dictionary with 'x' and 'y' keys for core rectangle center point\n"
        "- **core_width** (float): Width of the core rectangle\n"
        "- **core_height** (float): Height/depth of the core rectangle\n"
        "- **core_rotation** (float, optional): Rotation angle of the core in degrees (default: 0)\n"
        "- **building_height** (float): Total height of the building\n"
        "- **number_of_floors** (int): Number of floors in the building\n"
        "- **floor_to_floor_height** (float, optional): Height between floors (calculated from building_height if not provided)\n"
        "\n**Returns:**\n"
        "Dictionary containing the operation status, generated geometry information, and analysis metrics "
        "(gross floor area, volume, core-to-gross ratio, floor plate efficiency)."
    )
)
async def generate_building_massing(
    footprint_points: list,
    core_center: dict,
    core_width: float,
    core_height: float,
    core_rotation: float = 0,
    building_height: float = None,
    number_of_floors: int = None,
    floor_to_floor_height: float = None
) -> Dict[str, Any]:
    """
    Generate building massing model from parameters via HTTP bridge.

    Args:
        footprint_points: List of {x, y} coordinate dictionaries
        core_center: {x, y} dictionary for core center
        core_width: Width of core rectangle
        core_height: Height/depth of core rectangle
        core_rotation: Rotation angle in degrees (optional)
        building_height: Total building height
        number_of_floors: Number of floors
        floor_to_floor_height: Floor-to-floor height (optional)

    Returns:
        Dict containing operation results and analysis data
    """

    request_data = {
        "footprint_points": footprint_points,
        "core_center": core_center,
        "core_width": core_width,
        "core_height": core_height,
        "core_rotation": core_rotation,
        "building_height": building_height,
        "number_of_floors": number_of_floors,
        "floor_to_floor_height": floor_to_floor_height
    }

    return call_bridge_api("/generate_building_massing", request_data)

@bridge_handler("/generate_building_massing")
def handle_generate_building_massing(data):
    """Bridge handler for building massing generation"""
    try:
        pass

        ### Here is where we will put the handler for creating the building mass
        ### it can be contained entirely here or call helper functions that can be added to the end of this file
        ### The inputs to this function are a dictionary of key/value pairs that come from the input data
        ### Claude will collect (defined by the json structure in sample.json).

    except ImportError as e:
        import traceback
        return {
            "success": False,
            "error": f"Rhino/Grasshopper not available: {str(e)}",
            "traceback": traceback.format_exc()
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error generating building massing: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ============================================================================
# DELIVERED EXAMPLE GRASSHOPPER TOOLS
# ============================================================================

@gh_tool(
    name="list_gh_files",
    description=(
        "List all Grasshopper (.gh) files available in the Grasshopper File Library with their metadata. "
        "This tool scans the 'Tools/Grasshopper File Library' directory and returns "
        "all .gh files with detailed information from metadata.json including descriptions, "
        "inputs, outputs, categories, and workflow relationships.\n\n"
        "**Returns:**\n"
        "Dictionary containing list of available .gh files with their paths, metadata, "
        "and available workflows. Use this to understand what files are available and how they work together."
    )
)
async def list_gh_files() -> Dict[str, Any]:
    """
    List all .gh files in the Grasshopper File Library with metadata.

    Returns:
        Dict containing available files information and metadata
    """
    return call_bridge_api("/list_gh_files", {})

@bridge_handler("/list_gh_files")
def handle_list_gh_files(data):
    """Bridge handler for listing .gh files in the library with metadata"""
    try:
        import os
        import json

        # Get the library path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        library_path = os.path.join(script_dir, "Grasshopper File Library")

        if not os.path.exists(library_path):
            return {
                "success": False,
                "error": f"Grasshopper File Library folder not found at: {library_path}",
                "files": []
            }

        # Load metadata if available
        metadata_path = os.path.join(library_path, "metadata.json")
        metadata = None
        metadata_files = {}

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    # Create lookup by filename
                    if 'files' in metadata:
                        for file_meta in metadata['files']:
                            metadata_files[file_meta['filename']] = file_meta
            except Exception as e:
                # If metadata fails to load, continue without it
                pass

        # Find all .gh files recursively
        gh_files = []
        for root, dirs, files in os.walk(library_path):
            for file in files:
                if file.lower().endswith('.gh'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, library_path)

                    file_info = {
                        "name": file,
                        "relative_path": relative_path,
                        "full_path": full_path,
                        "size_bytes": os.path.getsize(full_path)
                    }

                    # Add metadata if available
                    if file in metadata_files:
                        file_meta = metadata_files[file]
                        file_info["description"] = file_meta.get("description", "")
                        file_info["category"] = file_meta.get("category", "")
                        file_info["tags"] = file_meta.get("tags", [])
                        file_info["inputs"] = file_meta.get("inputs", [])
                        file_info["outputs"] = file_meta.get("outputs", [])
                        file_info["workflow_position"] = file_meta.get("workflow_position")
                        file_info["dependencies"] = file_meta.get("dependencies", [])

                    gh_files.append(file_info)

        result = {
            "success": True,
            "files": gh_files,
            "count": len(gh_files),
            "library_path": library_path,
            "message": f"Found {len(gh_files)} Grasshopper file(s) in library"
        }

        # Include library info and workflows if metadata exists
        if metadata:
            if 'library_info' in metadata:
                result["library_info"] = metadata["library_info"]
            if 'workflows' in metadata:
                result["workflows"] = metadata["workflows"]
                result["workflow_count"] = len(metadata["workflows"])

        return result

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error listing .gh files: {str(e)}",
            "traceback": traceback.format_exc(),
            "files": []
        }

@gh_tool(
    name="set_grasshopper_slider",
    description=(
        "Change the value of a Grasshopper slider component by name in a specific Grasshopper file. "
        "This tool will activate the specified file (making it visible to the user), "
        "then find the slider component and update its value. "
        "Use 'get_active_gh_files' to see all open files and 'list_grasshopper_sliders' to see available sliders.\n\n"
        "**Parameters:**\n"
        "- **file_name** (str, required): Name of the .gh file containing the slider (e.g., 'Primary Truss Generator.gh')\n"
        "- **slider_name** (str): The name/nickname of the slider component to modify\n"
        "- **new_value** (float): The new value to set for the slider\n"
        "\n**Returns:**\n"
        "Dictionary containing the operation status and updated slider information."
    )
)
async def set_grasshopper_slider(file_name: str, slider_name: str, new_value: float) -> Dict[str, Any]:
    """
    Set the value of a Grasshopper slider by name via HTTP bridge.

    Args:
        file_name: Name of the .gh file containing the slider
        slider_name: Name of the slider component
        new_value: New value to set

    Returns:
        Dict containing operation results
    """

    request_data = {
        "file_name": file_name,
        "slider_name": slider_name,
        "new_value": new_value
    }

    return call_bridge_api("/set_slider", request_data)

@bridge_handler("/set_slider")
def handle_set_slider(data):
    """Bridge handler for set slider requests"""
    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import Rhino
        import System

        file_name = data.get('file_name', '')
        slider_name = data.get('slider_name', '')
        new_value = float(data.get('new_value', 0))

        # Ensure the correct file is active first
        activation_result = ensure_file_is_active(file_name)
        if not activation_result.get("success", False):
            return {
                "success": False,
                "error": activation_result.get("error", "Failed to activate file"),
                "file_name": file_name,
                "slider_name": slider_name,
                "new_value": new_value
            }

        # Get the Grasshopper plugin and document
        gh = Rhino.RhinoApp.GetPlugInObject("Grasshopper")
        if not gh:
            return {
                "success": False,
                "error": "Grasshopper plugin not available",
                "file_name": file_name,
                "slider_name": slider_name,
                "new_value": new_value
            }

        gh_doc = Grasshopper.Instances.ActiveCanvas.Document if Grasshopper.Instances.ActiveCanvas else None
        if not gh_doc:
            return {
                "success": False,
                "error": "No active Grasshopper document found",
                "file_name": file_name,
                "slider_name": slider_name,
                "new_value": new_value
            }

        # Find the slider component
        slider_found = False
        old_value = None
        clamped_value = new_value

        for obj in gh_doc.Objects:
            if isinstance(obj, Grasshopper.Kernel.Special.GH_NumberSlider):
                if (obj.NickName or "Unnamed") == slider_name:
                    slider_found = True
                    old_value = float(str(obj.Slider.Value))

                    # Clamp value to slider bounds
                    clamped_value = max(float(str(obj.Slider.Minimum)),
                                      min(float(str(obj.Slider.Maximum)), new_value))

                    # Set the new value
                    obj.Slider.Value = System.Decimal.Parse(str(clamped_value))

                    # Trigger solution recompute
                    gh_doc.NewSolution(True)

                    break

        if not slider_found:
            return {
                "success": False,
                "error": f"Slider '{slider_name}' not found",
                "slider_name": slider_name,
                "new_value": new_value
            }

        return {
            "success": True,
            "slider_name": slider_name,
            "old_value": old_value,
            "new_value": clamped_value,
            "clamped": clamped_value != new_value,
            "message": f"Slider '{slider_name}' updated to {clamped_value}" +
                      (f" (clamped from {new_value})" if clamped_value != new_value else "")
        }

    except ImportError as e:
        return {
            "success": False,
            "error": f"Grasshopper not available: {str(e)}",
            "slider_name": data.get('slider_name', ''),
            "new_value": data.get('new_value', 0)
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error setting slider: {str(e)}",
            "traceback": traceback.format_exc(),
            "slider_name": data.get('slider_name', ''),
            "new_value": data.get('new_value', 0)
        }

# ============================================================================
# EML PARAMETER DISCOVERY AND MANAGEMENT
# ============================================================================

@gh_tool(
    name="list_eml_parameters",
    description=(
        "Discover all EML (eml_) prefixed parameters in the active Grasshopper file. "
        "The eml_ naming convention is used to mark components for automated interaction "
        "and cross-file data exchange. This tool finds all components with names starting "
        "with 'eml_' including:\n\n"
        "- **Sliders**: Number sliders for numeric input\n"
        "- **Panels**: Text panels for output or input\n"
        "- **Boolean Toggles**: True/False switches\n"
        "- **Value Lists**: Dropdown selection components\n"
        "- **Number Primitives**: Number containers\n"
        "- **Text Primitives**: Text containers\n"
        "- **Integer Primitives**: Integer containers\n"
        "- **Geometry Parameters**: Curve, Brep, Line, Surface, Point, etc.\n\n"
        "Each parameter includes metadata about its type, current value, direction (input/output), "
        "and connection status to help with cross-file data exchange.\n\n"
        "**Returns:**\n"
        "Dictionary containing categorized lists of all eml_ parameters."
    )
)
async def list_eml_parameters() -> Dict[str, Any]:
    """
    List all eml_ prefixed parameters in the Grasshopper document.

    Returns:
        Dict containing categorized eml_ parameters
    """
    return call_bridge_api("/list_eml_parameters", {})

@bridge_handler("/list_eml_parameters")
def handle_list_eml_parameters(data):
    """Bridge handler for discovering all eml_ prefixed parameters"""
    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import Rhino

        # Get the Grasshopper plugin and document
        gh = Rhino.RhinoApp.GetPlugInObject("Grasshopper")
        if not gh:
            return {
                "success": False,
                "error": "Grasshopper plugin not available"
            }

        gh_doc = Grasshopper.Instances.ActiveCanvas.Document if Grasshopper.Instances.ActiveCanvas else None
        if not gh_doc:
            return {
                "success": False,
                "error": "No active Grasshopper document found"
            }

        # Storage for categorized parameters
        eml_params = {
            "sliders": [],
            "panels": [],
            "boolean_toggles": [],
            "value_lists": [],
            "number_primitives": [],
            "text_primitives": [],
            "integer_primitives": [],
            "geometry_params": []
        }

        # Scan all objects in the document
        for obj in gh_doc.Objects:
            try:
                nick_name = obj.NickName or ""
                if not nick_name.lower().startswith("eml_"):
                    continue

                # Get common properties
                obj_guid = str(obj.InstanceGuid)
                has_sources = hasattr(obj, 'SourceCount') and obj.SourceCount > 0
                has_recipients = hasattr(obj, 'Recipients') and obj.Recipients.Count > 0

                # Determine direction
                if has_sources and has_recipients:
                    direction = "passthrough"
                elif has_sources:
                    direction = "output"
                elif has_recipients:
                    direction = "input"
                else:
                    direction = "isolated"

                base_info = {
                    "name": nick_name,
                    "guid": obj_guid,
                    "direction": direction,
                    "has_sources": has_sources,
                    "has_recipients": has_recipients,
                    "description": obj.Description if hasattr(obj, 'Description') else ""
                }

                # 1. Number Sliders
                if isinstance(obj, Grasshopper.Kernel.Special.GH_NumberSlider):
                    eml_params["sliders"].append({
                        **base_info,
                        "current_value": float(str(obj.Slider.Value)),
                        "min_value": float(str(obj.Slider.Minimum)),
                        "max_value": float(str(obj.Slider.Maximum)),
                        "precision": obj.Slider.DecimalPlaces,
                        "slider_type": obj.Slider.Type.ToString()
                    })

                # 2. Panels
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_Panel):
                    panel_text = ""
                    if hasattr(obj, 'Properties') and hasattr(obj.Properties, 'UserText'):
                        panel_text = str(obj.Properties.UserText)

                    eml_params["panels"].append({
                        **base_info,
                        "text": panel_text,
                        "multiline": obj.Properties.Multiline if hasattr(obj, 'Properties') else True
                    })

                # 3. Boolean Toggles
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_BooleanToggle):
                    eml_params["boolean_toggles"].append({
                        **base_info,
                        "value": bool(obj.Value) if hasattr(obj, 'Value') else False
                    })

                # 4. Value Lists
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_ValueList):
                    selected_items = []
                    all_items = []

                    if hasattr(obj, 'ListItems'):
                        for item in obj.ListItems:
                            item_name = str(item.Name) if hasattr(item, 'Name') else str(item)
                            all_items.append(item_name)
                            if hasattr(item, 'Selected') and item.Selected:
                                selected_items.append(item_name)

                    eml_params["value_lists"].append({
                        **base_info,
                        "selected_items": selected_items,
                        "all_items": all_items
                    })

                # 5. Number Primitives
                elif type(obj).__name__ == 'GH_NumberParameter' or 'Param_Number' in type(obj).__name__:
                    values = []
                    if hasattr(obj, 'VolatileData'):
                        for branch in obj.VolatileData.Branches:
                            for item in branch:
                                try:
                                    values.append(float(str(item)))
                                except:
                                    pass

                    eml_params["number_primitives"].append({
                        **base_info,
                        "type": "Number",
                        "values": values,
                        "value_count": len(values)
                    })

                # 6. Integer Primitives
                elif type(obj).__name__ == 'GH_IntegerParameter' or 'Param_Integer' in type(obj).__name__:
                    values = []
                    if hasattr(obj, 'VolatileData'):
                        for branch in obj.VolatileData.Branches:
                            for item in branch:
                                try:
                                    values.append(int(str(item)))
                                except:
                                    pass

                    eml_params["integer_primitives"].append({
                        **base_info,
                        "type": "Integer",
                        "values": values,
                        "value_count": len(values)
                    })

                # 7. Text/String Primitives
                elif type(obj).__name__ == 'GH_StringParameter' or 'Param_String' in type(obj).__name__:
                    values = []
                    if hasattr(obj, 'VolatileData'):
                        for branch in obj.VolatileData.Branches:
                            for item in branch:
                                values.append(str(item))

                    eml_params["text_primitives"].append({
                        **base_info,
                        "type": "Text",
                        "values": values,
                        "value_count": len(values)
                    })

                # 8. Geometry Parameters
                elif any(geom_type in type(obj).__name__ for geom_type in [
                    'Param_Curve', 'Param_Surface', 'Param_Brep', 'Param_Geometry',
                    'Param_Line', 'Param_Circle', 'Param_Arc', 'Param_Point',
                    'Param_Mesh', 'Param_Plane', 'Param_Vector'
                ]):
                    geom_count = 0
                    if hasattr(obj, 'VolatileDataCount'):
                        geom_count = obj.VolatileDataCount

                    eml_params["geometry_params"].append({
                        **base_info,
                        "geometry_type": type(obj).__name__.replace('Param_', '').replace('GH_', ''),
                        "geometry_count": geom_count,
                        "has_geometry": geom_count > 0
                    })

            except Exception as e:
                # Skip components that cause errors
                continue

        # Calculate totals
        total_count = sum(len(v) for v in eml_params.values())

        return {
            "success": True,
            "eml_parameters": eml_params,
            "summary": {
                "total_count": total_count,
                "sliders": len(eml_params["sliders"]),
                "panels": len(eml_params["panels"]),
                "boolean_toggles": len(eml_params["boolean_toggles"]),
                "value_lists": len(eml_params["value_lists"]),
                "number_primitives": len(eml_params["number_primitives"]),
                "text_primitives": len(eml_params["text_primitives"]),
                "integer_primitives": len(eml_params["integer_primitives"]),
                "geometry_params": len(eml_params["geometry_params"])
            },
            "message": f"Found {total_count} eml_ prefixed parameters"
        }

    except ImportError as e:
        return {
            "success": False,
            "error": f"Grasshopper not available: {str(e)}"
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error discovering eml_ parameters: {str(e)}",
            "traceback": traceback.format_exc()
        }

@gh_tool(
    name="get_eml_parameter_value",
    description=(
        "Get the current value(s) from any eml_ prefixed parameter. "
        "Works with all parameter types including sliders, panels, toggles, primitives, "
        "and geometry parameters. For geometry parameters, returns metadata about the "
        "geometry rather than the actual geometry data.\n\n"
        "**Parameters:**\n"
        "- **parameter_name** (str): The name of the eml_ parameter (e.g., 'eml_panel_count')\n"
        "\n**Returns:**\n"
        "Dictionary containing the parameter value(s) and metadata."
    )
)
async def get_eml_parameter_value(parameter_name: str) -> Dict[str, Any]:
    """
    Get value from an eml_ parameter.

    Args:
        parameter_name: Name of the eml_ parameter

    Returns:
        Dict containing parameter value and metadata
    """
    request_data = {
        "parameter_name": parameter_name
    }

    return call_bridge_api("/get_eml_parameter_value", request_data)

@bridge_handler("/get_eml_parameter_value")
def handle_get_eml_parameter_value(data):
    """Bridge handler for getting eml_ parameter values"""
    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import Rhino

        parameter_name = data.get('parameter_name', '')

        # Get the Grasshopper plugin and document
        gh = Rhino.RhinoApp.GetPlugInObject("Grasshopper")
        if not gh:
            return {
                "success": False,
                "error": "Grasshopper plugin not available"
            }

        gh_doc = Grasshopper.Instances.ActiveCanvas.Document if Grasshopper.Instances.ActiveCanvas else None
        if not gh_doc:
            return {
                "success": False,
                "error": "No active Grasshopper document found"
            }

        # Find the parameter
        for obj in gh_doc.Objects:
            nick_name = obj.NickName or ""
            if nick_name.lower() == parameter_name.lower():
                # Slider
                if isinstance(obj, Grasshopper.Kernel.Special.GH_NumberSlider):
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "slider",
                        "value": float(str(obj.Slider.Value))
                    }

                # Panel
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_Panel):
                    panel_text = ""
                    if hasattr(obj, 'Properties') and hasattr(obj.Properties, 'UserText'):
                        panel_text = str(obj.Properties.UserText)
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "panel",
                        "value": panel_text
                    }

                # Boolean Toggle
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_BooleanToggle):
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "boolean_toggle",
                        "value": bool(obj.Value) if hasattr(obj, 'Value') else False
                    }

                # Value List
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_ValueList):
                    selected_items = []
                    if hasattr(obj, 'ListItems'):
                        for item in obj.ListItems:
                            if hasattr(item, 'Selected') and item.Selected:
                                selected_items.append(str(item.Name) if hasattr(item, 'Name') else str(item))
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "value_list",
                        "value": selected_items
                    }

                # Primitives (Number, Integer, Text)
                elif hasattr(obj, 'VolatileData'):
                    values = []
                    for branch in obj.VolatileData.Branches:
                        for item in branch:
                            values.append(str(item))

                    param_type = "unknown"
                    if 'Number' in type(obj).__name__:
                        param_type = "number"
                        values = [float(v) for v in values]
                    elif 'Integer' in type(obj).__name__:
                        param_type = "integer"
                        values = [int(v) for v in values]
                    elif 'String' in type(obj).__name__:
                        param_type = "text"
                    elif any(g in type(obj).__name__ for g in ['Curve', 'Brep', 'Surface', 'Point', 'Line']):
                        param_type = "geometry"
                        values = [f"{type(item).__name__}" for item in obj.VolatileData.AllData(True)]

                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": param_type,
                        "values": values,
                        "value_count": len(values)
                    }

        return {
            "success": False,
            "error": f"Parameter '{parameter_name}' not found",
            "parameter_name": parameter_name
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error getting parameter value: {str(e)}",
            "traceback": traceback.format_exc()
        }

@gh_tool(
    name="set_eml_parameter_value",
    description=(
        "Set the value of any eml_ prefixed parameter. "
        "Supports sliders, panels, boolean toggles, value lists, and primitive parameters. "
        "For geometry parameters, use the existing set_grasshopper_geometry_input tool.\n\n"
        "**Parameters:**\n"
        "- **parameter_name** (str): The name of the eml_ parameter\n"
        "- **value** (any): The value to set (type depends on parameter type)\n"
        "  - Slider: float/int\n"
        "  - Panel: string\n"
        "  - Boolean: true/false\n"
        "  - Value List: string (item name)\n"
        "  - Number/Integer: float/int\n"
        "  - Text: string\n"
        "\n**Returns:**\n"
        "Dictionary containing the operation status."
    )
)
async def set_eml_parameter_value(parameter_name: str, value: Any) -> Dict[str, Any]:
    """
    Set value for an eml_ parameter.

    Args:
        parameter_name: Name of the eml_ parameter
        value: Value to set

    Returns:
        Dict containing operation results
    """
    request_data = {
        "parameter_name": parameter_name,
        "value": value
    }

    return call_bridge_api("/set_eml_parameter_value", request_data)

@bridge_handler("/set_eml_parameter_value")
def handle_set_eml_parameter_value(data):
    """Bridge handler for setting eml_ parameter values"""
    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import Rhino
        import System

        parameter_name = data.get('parameter_name', '')
        value = data.get('value')

        # Get the Grasshopper plugin and document
        gh = Rhino.RhinoApp.GetPlugInObject("Grasshopper")
        if not gh:
            return {
                "success": False,
                "error": "Grasshopper plugin not available"
            }

        gh_doc = Grasshopper.Instances.ActiveCanvas.Document if Grasshopper.Instances.ActiveCanvas else None
        if not gh_doc:
            return {
                "success": False,
                "error": "No active Grasshopper document found"
            }

        # Find and set the parameter
        for obj in gh_doc.Objects:
            nick_name = obj.NickName or ""
            if nick_name.lower() == parameter_name.lower():
                # Slider
                if isinstance(obj, Grasshopper.Kernel.Special.GH_NumberSlider):
                    new_value = float(value)
                    clamped_value = max(float(str(obj.Slider.Minimum)),
                                      min(float(str(obj.Slider.Maximum)), new_value))
                    obj.Slider.Value = System.Decimal.Parse(str(clamped_value))
                    gh_doc.NewSolution(True)
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "slider",
                        "old_value": None,
                        "new_value": clamped_value
                    }

                # Panel
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_Panel):
                    if hasattr(obj, 'Properties'):
                        obj.Properties.UserText = str(value)
                    gh_doc.NewSolution(True)
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "panel",
                        "new_value": str(value)
                    }

                # Boolean Toggle
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_BooleanToggle):
                    obj.Value = bool(value)
                    gh_doc.NewSolution(True)
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "boolean_toggle",
                        "new_value": bool(value)
                    }

                # Value List
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_ValueList):
                    if hasattr(obj, 'ListItems'):
                        for item in obj.ListItems:
                            item_name = str(item.Name) if hasattr(item, 'Name') else str(item)
                            if item_name.lower() == str(value).lower():
                                item.Selected = True
                            else:
                                item.Selected = False
                    gh_doc.NewSolution(True)
                    return {
                        "success": True,
                        "parameter_name": nick_name,
                        "type": "value_list",
                        "new_value": str(value)
                    }

                # For primitives, we can't directly set values as they receive from upstream
                else:
                    return {
                        "success": False,
                        "error": f"Parameter type '{type(obj).__name__}' does not support direct value setting (primitives receive values from connected components)",
                        "parameter_name": nick_name
                    }

        return {
            "success": False,
            "error": f"Parameter '{parameter_name}' not found",
            "parameter_name": parameter_name
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error setting parameter value: {str(e)}",
            "traceback": traceback.format_exc()
        }

@gh_tool(
    name="suggest_eml_connections",
    description=(
        "Analyze eml_ parameters in the current Grasshopper file and suggest potential "
        "data connections between them. This tool identifies output parameters that could "
        "feed into input parameters based on type compatibility and naming patterns. "
        "Particularly useful for understanding data flow and setting up cross-file data exchange.\n\n"
        "The tool categorizes parameters by direction:\n"
        "- **Outputs**: Parameters with data that could be extracted\n"
        "- **Inputs**: Parameters waiting for data input\n"
        "- **Isolated**: Parameters with no connections\n\n"
        "It then suggests compatible connections based on data types.\n\n"
        "**Returns:**\n"
        "Dictionary containing parameter categorization and suggested connections."
    )
)
async def suggest_eml_connections() -> Dict[str, Any]:
    """
    Analyze and suggest connections between eml_ parameters.

    Returns:
        Dict containing connection suggestions
    """
    return call_bridge_api("/suggest_eml_connections", {})

@bridge_handler("/suggest_eml_connections")
def handle_suggest_eml_connections(data):
    """Bridge handler for suggesting eml_ parameter connections"""
    try:
        import clr
        clr.AddReference('Grasshopper')
        import Grasshopper
        import Rhino

        # Get the Grasshopper plugin and document
        gh = Rhino.RhinoApp.GetPlugInObject("Grasshopper")
        if not gh:
            return {
                "success": False,
                "error": "Grasshopper plugin not available"
            }

        gh_doc = Grasshopper.Instances.ActiveCanvas.Document if Grasshopper.Instances.ActiveCanvas else None
        if not gh_doc:
            return {
                "success": False,
                "error": "No active Grasshopper document found"
            }

        # Get file information
        file_path = str(gh_doc.FilePath) if gh_doc.FilePath else "Untitled"
        file_name = os.path.basename(file_path) if file_path != "Untitled" else "Untitled"

        # Categorize parameters
        outputs = []  # Has data, could export
        inputs = []   # Waiting for data
        isolated = [] # No connections

        for obj in gh_doc.Objects:
            try:
                nick_name = obj.NickName or ""
                if not nick_name.lower().startswith("eml_"):
                    continue

                obj_guid = str(obj.InstanceGuid)
                has_sources = hasattr(obj, 'SourceCount') and obj.SourceCount > 0
                has_recipients = hasattr(obj, 'Recipients') and obj.Recipients.Count > 0
                has_data = False
                data_count = 0

                # Check for data
                if hasattr(obj, 'VolatileDataCount'):
                    data_count = obj.VolatileDataCount
                    has_data = data_count > 0

                # Determine parameter type
                param_type = "unknown"
                if isinstance(obj, Grasshopper.Kernel.Special.GH_NumberSlider):
                    param_type = "slider_number"
                    has_data = True
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_Panel):
                    param_type = "panel_text"
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_BooleanToggle):
                    param_type = "boolean"
                    has_data = True
                elif isinstance(obj, Grasshopper.Kernel.Special.GH_ValueList):
                    param_type = "value_list"
                    has_data = True
                elif 'Number' in type(obj).__name__:
                    param_type = "number"
                elif 'Integer' in type(obj).__name__:
                    param_type = "integer"
                elif 'String' in type(obj).__name__:
                    param_type = "text"
                elif 'Curve' in type(obj).__name__:
                    param_type = "curve"
                elif 'Brep' in type(obj).__name__:
                    param_type = "brep"
                elif 'Surface' in type(obj).__name__:
                    param_type = "surface"
                elif 'Point' in type(obj).__name__:
                    param_type = "point"
                elif 'Line' in type(obj).__name__:
                    param_type = "line"
                elif 'Mesh' in type(obj).__name__:
                    param_type = "mesh"

                param_info = {
                    "name": nick_name,
                    "type": param_type,
                    "guid": obj_guid,
                    "has_data": has_data,
                    "data_count": data_count
                }

                # Categorize by connection status
                if has_sources and not has_recipients:
                    # Has input but no output = terminal/output
                    if has_data:
                        outputs.append(param_info)
                    else:
                        isolated.append(param_info)
                elif has_recipients and not has_sources:
                    # Has output but no input = source/input
                    if has_data:
                        outputs.append(param_info)
                    else:
                        inputs.append(param_info)
                elif not has_sources and not has_recipients:
                    # No connections
                    if has_data:
                        outputs.append(param_info)
                    else:
                        isolated.append(param_info)
                else:
                    # Has both = passthrough
                    if has_data:
                        outputs.append(param_info)

            except Exception as e:
                continue

        # Suggest connections based on type compatibility
        suggestions = []
        for output_param in outputs:
            for input_param in inputs:
                # Check type compatibility
                compatible = False
                reason = ""

                output_type = output_param["type"]
                input_type = input_param["type"]

                # Exact type match
                if output_type == input_type:
                    compatible = True
                    reason = f"Exact type match: {output_type}"

                # Numeric compatibility
                elif output_type in ["slider_number", "number", "integer"] and input_type in ["number", "integer"]:
                    compatible = True
                    reason = "Numeric types are compatible"

                # Text compatibility
                elif output_type in ["panel_text", "text", "value_list"] and input_type in ["text", "panel_text"]:
                    compatible = True
                    reason = "Text types are compatible"

                # Geometry compatibility (broader)
                elif output_type in ["curve", "line"] and input_type in ["curve", "geometry"]:
                    compatible = True
                    reason = f"{output_type.capitalize()} can be used as curve input"
                elif output_type in ["brep", "surface"] and input_type in ["brep", "surface", "geometry"]:
                    compatible = True
                    reason = f"{output_type.capitalize()} can be used as surface/brep input"

                # Name similarity (suggests intent)
                name_similarity = 0
                output_words = output_param["name"].lower().replace("eml_", "").split("_")
                input_words = input_param["name"].lower().replace("eml_", "").split("_")
                common_words = set(output_words) & set(input_words)
                if common_words:
                    name_similarity = len(common_words) / max(len(output_words), len(input_words))
                    if name_similarity > 0.3:
                        compatible = True
                        reason += f" (names suggest related purpose: {', '.join(common_words)})"

                if compatible:
                    suggestions.append({
                        "from_parameter": output_param["name"],
                        "from_type": output_type,
                        "to_parameter": input_param["name"],
                        "to_type": input_type,
                        "reason": reason,
                        "confidence": "high" if output_type == input_type else "medium"
                    })

        return {
            "success": True,
            "file_name": file_name,
            "file_path": file_path,
            "outputs": outputs,
            "inputs": inputs,
            "isolated": isolated,
            "suggestions": suggestions,
            "summary": {
                "total_eml_params": len(outputs) + len(inputs) + len(isolated),
                "output_params": len(outputs),
                "input_params": len(inputs),
                "isolated_params": len(isolated),
                "suggested_connections": len(suggestions)
            },
            "message": f"Analyzed {len(outputs) + len(inputs) + len(isolated)} eml_ parameters and found {len(suggestions)} potential connections"
        }

    except ImportError as e:
        return {
            "success": False,
            "error": f"Grasshopper not available: {str(e)}"
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error analyzing connections: {str(e)}",
            "traceback": traceback.format_exc()
        }

# All tools automatically registered via decorators
