import os
import re
import shutil
from typing import Tuple
import xml.etree.ElementTree as ET

TEMP_DIR = "temp_epub_dir"

class FailureException(Exception):
    pass

def reset_temp_dir():
    """Deletes the temp directory and recreates it."""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)  # Safely remove a directory and all its contents
    os.makedirs(TEMP_DIR)  # Recreate the temp directory

def unzip_epub(epub_path, temp_dir):
    """Unzips the EPUB file into the specified temporary directory."""
    os.system(f"unzip -q {epub_path} -d {temp_dir}")

def find_content_file(temp_dir) -> str:
    """Finds the default content file specified in the container.xml."""
    container_path = os.path.join(temp_dir, "META-INF/container.xml")
    with open(container_path, "r") as f:
        container_xml = f.read()
    rootfile = re.search(r'<rootfile.*?full-path="([^"]+)"', container_xml).group(1)
    return rootfile

def get_spines(content_file) -> Tuple[int, ET.Element]:
    """Gets the spine element and its index from the content file."""
    try:
        with open(f"{TEMP_DIR}/{content_file}", "r") as f:
            xml_content = f.read()
    except FileNotFoundError:
        raise FailureException(f"ERROR: Could not find {content_file} in {TEMP_DIR} while trying to get spines")
    
    tree = ET.ElementTree(ET.fromstring(xml_content))
    root = tree.getroot()

    if root.tag.endswith("package"):
        package_element = root
    else:
        raise FailureException(f"ERROR: Could not find package tag in {content_file}")
    
    spine_element = None
    spine_index = 0
    for index, child in enumerate(package_element, start=1):
        if child.tag.endswith('spine') or child.tag == 'spine':
            spine_element = child
            spine_index = index * 2
            break
    
    if spine_element is None:
        raise FailureException(f"ERROR: Could not find spine tag in {content_file}")

    return spine_index, spine_element, package_element

def id_str(element: ET.Element) -> str:
    if id := element.get("id"):
        return f"[{id}]"
    return ""

def grab_root_element_from_file(file_name: str) -> ET.Element:
    """Grabs the root XML element from a file."""
    try:
        with open(file_name, "r") as f:
            xml_content = f.read()
    except FileNotFoundError:
        raise FailureException(f"ERROR: Could not find {file_name} in {TEMP_DIR} while trying to get spines")
    
    tree = ET.ElementTree(ET.fromstring(xml_content))
    return tree.getroot()

def get_root_dir(content_file) -> str:
    """Returns the root directory of the content file."""
    if "/" in content_file:
        return os.path.dirname(content_file)
    return ""

def find_str_from_cfi_in_epub(epub_path, cfi, TEMP_DIR_OVERRIDE=TEMP_DIR) -> str:
    """Finds a string from the CFI (Canonical Fragment Identifier) in the EPUB file."""
    global TEMP_DIR
    TEMP_DIR = TEMP_DIR_OVERRIDE if TEMP_DIR_OVERRIDE else "temp_epub_dir"

    if TEMP_DIR == "temp_epub_dir":
        reset_temp_dir()
        unzip_epub(epub_path, TEMP_DIR)

    content_file = find_content_file(TEMP_DIR)
    root_dir = get_root_dir(content_file)
    
    cfi_chunks = cfi.split("/")
    chunks_index = 0
    if cfi_chunks[chunks_index] == "":
        chunks_index += 1
    
    chunk_groups = re.search(r'(?P<index>\d+){1}(?:\[(?P<id>.*)\])?(?P<extra>.)*', cfi_chunks[chunks_index])
    index = int(chunk_groups.group("index"))
    id = chunk_groups.group("id")
    extra = chunk_groups.group("extra")
    
    if index % 2 != 0:
        raise FailureException(f"ERROR: Spine index must be even, but got {index}")
    
    spine_index, spine_element, package_element = get_spines(content_file)
    manifest = get_manifest(package_element)
    
    if not len(manifest):
        raise FailureException(f"ERROR: Could not find manifest tag in package")
    
    if index != spine_index:
        raise FailureException(f"ERROR: Spine index must match the spine index in the content file. Got {index} but expected {spine_index}")
    
    chunks_index += 1
    current_element = spine_element
    in_spine = True

    while chunks_index < len(cfi_chunks):
        if ":" in cfi_chunks[chunks_index]:
            if id := current_element.get("id"):
                # print(id)
                ...
            return current_element.text
        
        chunk_groups = re.search(r'(?P<index>\d+){1}(?:\[(?P<id>.*)\])?(?P<extra>.)*', cfi_chunks[chunks_index])
        index = int(chunk_groups.group("index"))
        id = chunk_groups.group("id")
        extra = chunk_groups.group("extra")
        
        next_element = grab_xth_child(current_element, index, id, extra, in_spine, manifest, root_dir)
        chunks_index += 1
        in_spine = False
        current_element = next_element

    return ""

def grab_xth_child(element: ET.Element, index: int, id: str, extra: str, in_spine: bool, manifest, root_dir: str) -> ET.Element:
    """Grabs the xth child of an element."""
    if index % 2 != 0:
        raise FailureException(f"ERROR: index must be even, but got {index}")
    if index == 0:
        raise FailureException(f"ERROR: Spine index must be greater than 0, but got {index}")
    index = int(index / 2)
    
    if index > len(element):
        raise FailureException(f"ERROR: Spine index must be less than or equal to the number of children, but got {index}")
    
    if id:
        if id != element[index - 1].get("id"):
            raise FailureException(f"ERROR: The id of the child does not match the id in the CFI. Got {element[index - 1].get('id')} but expected {id}")
    
    elem = element[index - 1]
    if extra and "!" in extra:
        if in_spine:
            idref = elem.get("idref")
            if not idref:
                raise FailureException(f"ERROR: Expected idref attribute in itemref tag, but got None")
            item = manifest.find(f".//*[@id='{idref}']")
            if href := item.get("href"):
                path = f"{TEMP_DIR}/{root_dir}/{href}" if root_dir else f"{TEMP_DIR}/{href}"
                elem = grab_root_element_from_file(path)
                return elem
    return elem

def get_manifest(package_element: ET.Element) -> ET.Element:
    """Gets the manifest element from the package element."""
    for child in package_element:
        if child.tag.endswith('manifest') or child.tag == 'manifest':
            return child
    return None

def find_cfi_from_str_in_epub(epub_path, str_to_search_for):
    cfi = "/"

    if TEMP_DIR == "temp_epub_dir":
        # Empty out our temp directory
        reset_temp_dir()
        # Unzip the epub file to our temp directory
        unzip_epub(epub_path, TEMP_DIR)
    

#     For a Standard EPUB CFI, the leading step in the CFI must start with a slash (/) followed by an even number that references the spine child element of the Package Document's root package element. The Package Document traversed by the CFI must be the one specified as the Default Rendition in the EPUB Publication's META-INF/container.xml file (i.e., the Package Document referenced by the first rootfile element in container.xml).

# For an Intra-Publication EPUB CFI, the first step must start with a slash followed by a node number that references a position in Package Document starting from the root package element.

    # Check the META-INF/container.xml file to find the default rendition
    content_file = find_content_file(TEMP_DIR)
    print(f"Default rendition: {content_file}")

    spine_index, spine_element, package_element = get_spines(content_file)
    cfi += f"{spine_index}{id_str(spine_element)}/"
    
    return cfi
if __name__ == "__main__":
    str_to_search_for = "Some string to search for"
    epub_path = "test_epub_1.epub"
    TEMP_DIR = "test_epub_1"

    try:
        cfi = find_str_from_cfi_in_epub(epub_path, str_to_search_for)
        print(cfi)
    except FailureException as e:
        print(e)
