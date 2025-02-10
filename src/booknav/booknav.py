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

def unzip_epub(epub_path):
    """Unzips the EPUB file into the specified temporary directory."""
    os.system(f"unzip -q {epub_path} -d {TEMP_DIR}")

def find_content_file() -> str:
    """Finds the default content file specified in the container.xml."""
    container_path = os.path.join(TEMP_DIR, "META-INF/container.xml")
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

def grab_xth_child(element: ET.Element, index: int, id: str, extra: str, in_spine: bool, manifest, root_dir: str) -> Tuple[ET.Element, str]:
    """Grabs the xth child of an element and return path to file if we jump to a different file."""
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
                return elem, path
    return elem, ""

def get_manifest(package_element: ET.Element) -> ET.Element:
    """Gets the manifest element from the package element."""
    for child in package_element:
        if child.tag.endswith('manifest') or child.tag == 'manifest':
            return child
    return None

def find_item_id_with_href_in_manifest(manifest: ET.Element, href: str) -> str:
    for item in manifest:
        if item.get("href") == href:
            id = item.get("id")
            return id
    raise FailureException(f"ERROR: Could not find item with {href} in manifest inside content file")

def find_item_ref_index(spine_element: ET.Element, item_id: str) -> int:
    for index, itemref in enumerate(spine_element, start=1):
        if itemref.get("idref") == item_id:
            return index * 2
    raise FailureException(f"ERROR: Could not find itemref with {item_id} in spine element")

def find_path_in_xml(element, target, path=None):
    """ Recursively finds the path to the first occurrence of koboSpan with id 'target'. """
    if path is None:
        path = []

    for i, child in enumerate(element, start=1):
        # if <span class="koboSpan" id="kobo.15.3">
        if child.get("id") == target and child.get("class") == "koboSpan":
            return path + [(i*2, child.get("id"))]

        # Recursively search in child nodes
        result = find_path_in_xml(child, target, path + [(i*2, child.get("id"))])
        if result:
            return result

    return None

def kobo_to_cfi(epub_path: str, kobo_location_source: str, kobo_span: str) -> str:
    reset_temp_dir()
    unzip_epub(epub_path)

    content_file = find_content_file()
    root_dir = get_root_dir(content_file)
    
    spine_index, spine_element, package_element = get_spines(content_file)
    manifest = get_manifest(package_element)

    file_to_search_for = kobo_location_source
    if root_dir:
        if kobo_location_source.startswith(root_dir):
            file_to_search_for = kobo_location_source[len(root_dir)+1:]
    item_id = find_item_id_with_href_in_manifest(manifest, file_to_search_for)
    item_ref_index = find_item_ref_index(spine_element, item_id)

    cfi = f"/{spine_index}/{item_ref_index}!/"

    # read html file as xml 
    with open(f"{TEMP_DIR}/{kobo_location_source}", "r") as f:
        html_content_as_str = f.read()
    xml_content = ET.fromstring(html_content_as_str)
    # search for kobo_span
    path = find_path_in_xml(xml_content, kobo_span)
    if path:
        for index, id in path:
            id_str = f"[{id}]" if id else ""
            cfi += f"{index}{id_str}/"
    else:
        raise FailureException(f"ERROR: Could not find {kobo_span} in {kobo_location_source}")

    return cfi

def cfi_to_element(epub_path: str, cfi: str) -> Tuple[ET.Element, str]:

    reset_temp_dir()
    unzip_epub(epub_path)

    content_file = find_content_file()
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

    found_file_path = ""
    while chunks_index < len(cfi_chunks):
        if ":" in cfi_chunks[chunks_index]:
            if id := current_element.get("id"):
                # this id should be the kobo span id but we can grab it from the cfi more easily anyways
                # print(id)
                ...
            return current_element, found_file_path
        
        chunk_groups = re.search(r'(?P<index>\d+){1}(?:\[(?P<id>.*)\])?(?P<extra>.)*', cfi_chunks[chunks_index])
        index = int(chunk_groups.group("index"))
        id = chunk_groups.group("id")
        extra = chunk_groups.group("extra")
        
        next_element, file_path = grab_xth_child(current_element, index, id, extra, in_spine, manifest, root_dir)
        if file_path:
            found_file_path = file_path
        chunks_index += 1
        in_spine = False
        current_element = next_element

    raise FailureException(f"ERROR: Could not find {cfi} in {epub_path}")

def find_str_from_cfi_in_epub(epub_path, cfi) -> str:
    """Finds a string from the CFI (Canonical Fragment Identifier) in the EPUB file."""
    element, _ = cfi_to_element(epub_path, cfi)
    return element.text

def cfi_to_kobo(epub_path: str, cfi: str) -> Tuple[str, str]:
    """Converts a CFI to a Kobo span and file path."""
    re_result = re.search(r'kobo\.\d+\.\d+', cfi)
    if not re_result:
        raise FailureException(f"ERROR: Could not find kobo span in {cfi}")
    kobo_span = re_result.group(0)
    if not kobo_span:
        raise FailureException(f"ERROR: Could not find kobo_span in {cfi}")
    _, file_path = cfi_to_element(epub_path, cfi)
    file_path = file_path[file_path.find(TEMP_DIR) + len(TEMP_DIR) + 1:]
    return kobo_span, file_path

if __name__ == "__main__":
    str_to_search_for = "Some string to search for"
    epub_path = "test_epub_1.epub"

    try:
        cfi = find_str_from_cfi_in_epub(epub_path, str_to_search_for)
        print(cfi)
    except FailureException as e:
        print(e)
