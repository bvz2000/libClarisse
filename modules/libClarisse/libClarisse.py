import os.path
import re
import tempfile
import time

try:
    import ix
except ImportError:
    ix = None

"""
A series of useful libClarisse functions.
"""


# ------------------------------------------------------------------------------
def pdir_to_path(path, project_p):
    """
    Given a project path, convert path to an absolute path if it contains the
    variable $PDIR. If it does not contain this variable, return path unchanged.

    :param path: The path that may or may not contain $PDIR.
    :param project_p: The path to the project against which $PDIR is referenced.

    :return: An absolute path where $PDIR has been converted to a real dir. Does
             no checking to ensure that this path actually exists.
    """

    if project_p.endswith(".project"):
        project_p = os.path.split(project_p)[0]

    path = path.replace("$PDIR", project_p)
    path = os.path.abspath(path)

    return path


# ------------------------------------------------------------------------------
def clarisse_array_to_python_list(clarisse_array):
    """
    Convert a libClarisse array to a python list.

    :param clarisse_array: The libClarisse array.

    :return: A python list with the same items in it.
    """

    output = list()
    for i in range(clarisse_array.get_count()):
        output.append(clarisse_array[i])

    return output


# ------------------------------------------------------------------------------
def selection_to_context_list():
    """
    Takes in the selection and returns a list of contexts.

    :return:
    """

    items = clarisse_array_to_python_list(ix.selection)
    contexts = list()
    for item in items:
        if item.is_context():
            contexts.append(item)

    return contexts


# ------------------------------------------------------------------------------
def create_context(context_url):
    """
    Create contexts recursively (if they already exist, nothing happens)

    :param context_url: The URL of the context(s) to create

    :return: The context object that was created.
    """

    tokens = context_url.replace("project://", "/").split("/")

    url = "project:/"
    context = ix.item_exists(url)
    for token in tokens:
        url += "/" + token
        context = ix.item_exists(url)
        if not context:
            context = ix.create_context(url)

    return context


# ------------------------------------------------------------------------------
def copy_node(node, dest_context_url, leave_breadcrumb=False,
              breadcrumb_section="CLAM"):
    """
    Given a node, copy that node to the destination url (which must be a
    context). If the destination context does not exist, it will be created.

    :param node: The node object to be copied.
    :param dest_context_url: The context where the node will be copied to.
    :param leave_breadcrumb: If True, a custom attribute will be added to the
           node indicating where it was copied from.
    :param breadcrumb_section: The breadcrumb will be put into a section of
           this name. Defaults to "CLAM"

    :return: A full URL to the node that was copied.
    """

    dest_context = ix.item_exists(dest_context_url)
    if not dest_context:
        dest_context = create_context(dest_context_url)

    instance = dest_context.add_instance(node)
    instance.make_local()

    if leave_breadcrumb:
        ix.cmds.CreateCustomAttribute([instance.get_full_name()],
                                      "copied_from", 3,
                                      ["container", "vhint", "group", "count",
                                       "allow_expression"],
                                      ["CONTAINER_SINGLE",
                                       "VISUAL_HINT_DEFAULT",
                                       breadcrumb_section, "1", "0"])
        ix.application.check_for_events()
        ix.cmds.SetValues([instance.get_full_name() + ".copied_from[0]"],
                          [node.get_full_name])

    ix.application.check_for_events()
    return instance


# ------------------------------------------------------------------------------
def get_all_contexts(context, recursive):
    """
    Returns a python list of all the child contexts. If recursive is True, then
    it will return all contexts recursively.

    :param context: The context to search.
    :param recursive: If True, then all sub-contexts will be examined as well.
           Defaults to True.

    :return: A list of contexts.
    """

    output = list()

    flags = ix.api.CoreBitFieldHelper()
    ctx_array = ix.api.OfItemVector()

    if not recursive:
        context.get_items(ctx_array, flags)
    else:
        context.get_all_items(ctx_array, flags)

    items = clarisse_array_to_python_list(ctx_array)
    for item in items:
        if item.is_context():
            output.append(item)

    return output


# ------------------------------------------------------------------------------
def get_reference_file_path(context):
    """
    Returns the path to the file of a referenced context.

    :param context: The context that is a reference.

    :return: A path to the file being referenced.
    """

    if context.is_reference():
        return context.get_attribute("filename").get_string()
    else:
        raise TypeError("Context is not a reference")


# ------------------------------------------------------------------------------
def filter_contexts_to_references_only(contexts, project=True, abc=True,
                                       usd=True):
    """
    Given a python list of contexts, filter out any that are not references.
    If project is True, then include references to other libClarisse projects.
    If abc is True, then include references to alembic files. If usd is True,
    then include references to USD files. If none of these are true, only an
    empty list will be returned.

    :param contexts: A list of contexts we are filtering.
    :param project: If True, then references to libClarisse projects will be
           included in the output list.
    :param abc: If True, then references to alembic files will be included in
           the output list.
    :param usd: If True, then references to USD files will be included in the
           output list.

    :return: A list of contexts that are references (included types depending
             on which flags are set to True).
    """

    output = list()

    for context in contexts:

        if context.is_reference():
            if project:
                if get_reference_file_path(context).endswith(".project"):
                    output.append(context)
            if abc:
                if get_reference_file_path(context).endswith(".abc"):
                    output.append(context)
            if usd:
                if get_reference_file_path(context).endswith(".usd"):
                    output.append(context)

    return output


# ------------------------------------------------------------------------------
def get_all_objects(context):
    """
    Returns a python list of all the child objects (recursively) of the passed
    context.

    :param context:
    :return:
    """
    nodes_array = ix.api.OfObjectArray()
    context.get_all_objects("ProjectItem", nodes_array)

    return clarisse_array_to_python_list(nodes_array)


# ------------------------------------------------------------------------------
def get_all_attributes(node, type_filter=None):
    """
    Returns a python list of all the attribute objects for the object: "object".

    :param node: The node we want to collect attributes from.
    :param type_filter: A list of types to limit the output list to. Defaults to
           None. Options (as of Clarisse 3.6sp7) are:

        TYPE_BOOL = 0,
        TYPE_LONG = 1,
        TYPE_DOUBLE = 2,
        TYPE_STRING = 3,
        TYPE_FILE = 4,
        TYPE_REFERENCE = 5,
        TYPE_OBJECT = 6,
        TYPE_CURVE = 7,
        TYPE_ACTION = 8,

    :return: A python list of attributes.
    """

    output = list()
    if type_filter is not None and type(type_filter) is not list:
        type_filter = [type_filter]

    attribute_count = node.get_attribute_count()
    for i in range(0, attribute_count):
        attr = node.get_attribute(i)
        if not type_filter or attr.get_type() in type_filter:
            output.append(attr)

    return output


# ------------------------------------------------------------------------------
def get_all_attribute_values(attribute):
    """
    Returns a python lost of all the values for a specified attribute object.

    :param attribute: The attribute object for which we want the values.

    :return: A python list of the values attached to this attribute.
    """

    # Get all the values of this attribute
    values_array = ix.api.OfObjectArray()
    attribute.get_values(values_array)

    return clarisse_array_to_python_list(values_array)


# ------------------------------------------------------------------------------
def get_external_dependencies(context):
    """
    For the given context, list all of the external dependencies.

    :param context: The context for which we want the external dependencies.

    :return: A tuple of two python lists (external references, external
             sources).
    """

    ext_refs = ix.api.OfItemSet()
    ext_sources = ix.api.OfItemSet()
    context.get_external_dependencies(ext_refs, ext_sources)

    return (clarisse_array_to_python_list(ext_refs),
            clarisse_array_to_python_list(ext_sources))


# ------------------------------------------------------------------------------
def contexts_are_atomic(contexts):
    """
    For each context passed in the list: contexts, checks to see if they have
    any external dependencies. Returns True if they do, False otherwise.

    :param contexts: A list of contexts to check.

    :return: True if any of the contexts have external dependencies. False
             otherwise.
    """

    # If contexts is not a list, make it one now
    if not type(contexts) == list:
        contexts = [contexts]

    for context in contexts:

        # Skip non-contexts
        if not context.is_context():
            print context.get_name() + " is not a context. Skipping."
            continue

        ext_refs, ext_sources = get_external_dependencies(context)

        if len(ext_refs) > 0 or len(ext_sources) > 0:
            return False
        return True

    return True


# ------------------------------------------------------------------------------
def export_context_with_deps(context, dest, overwrite=False):
    """
    Exports the context passed to an external file without changing the open
    project. The file will be saved into the location specified by dest, and
    with a file name that matches the context name. If the file already exists,
    and if overwrite is False, an error is raised. If overwrite is True, then
    the file will be overwritten.

    :param context: A context to export as a project with dependencies.
    :param dest: The directory where the contexts should be exported. If this
           directory does not exist or is a file, an AssertionError will be
           raised.
    :param overwrite: If the destination file already exists, if overwrite is
           set to True then these files will be overwritten. If overwrite is
           False, then an IOError will be raised.

    :return: The path to the exported project.
    """

    assert(os.path.exists(dest))
    assert(os.path.isdir(dest))

    file_p = os.path.join(dest, context.get_name() + ".project")
    if os.path.exists(file_p):
        if not overwrite:
            msg = "File exists and overwrite is False: " + file_p
            raise IOError(msg)
    file_p = os.path.join(dest, context.get_name() + ".project")
    ix.export_context_as_project_with_dependencies(context, file_p)

    return file_p


# ------------------------------------------------------------------------------
def make_contexts_atomic(contexts):
    """
    For each of the contexts passed in the list: contexts, make this context
    atomic (have no external dependencies).

    :param contexts: A list of contexts to make atomic.

    :return: Nothing.
    """

    # If contexts is not a list, make it one now
    if not type(contexts) == list:
        contexts = [contexts]

    for context in contexts:

        # ix.application.disable()

        proj_p = export_context_with_deps(context, tempfile.gettempdir(), True)
        ix.application.check_for_events()

        temp_n = str(time.time()) + ".project"
        temp_p = os.path.join(tempfile.gettempdir(), temp_n)
        ix.cmds.ExportContextAsReference(context, temp_p)
        ix.application.check_for_events()
        ix.cmds.SetReferenceFilename([context], proj_p)
        ix.application.check_for_events()
        ix.cmds.MakeLocalContexts([context])
        os.remove(temp_p)


# ------------------------------------------------------------------------------
def create_metadata_node(context, data, name):
    """
    Given a context, this will create a metadata node in that location, fill it
    with the data from the data list, and then lock it.

    :param context: A clarisse context inside of which we will be creating the
           metadata node.
    :param data: A list of category-key-value-type sub-lists that will be stored
           as attributes in this node. Example: [[cat, key, value, type],
           [cat2, key2, value2, type2], ... ]
    :param name: The name of the metadata node to create.

    :return: Nothing
    """

    meta_node = context.item_exists(name)

    if meta_node is not None:

        # Unlock the object
        ix.cmds.UnlockItems([meta_node.get_full_name()])

    else:

        # Create the metadata object
        meta_node = context.add_object(name, "ProjectItem")

    # Add or change the metadata on the object
    for item in data:
        set_custom_attr(meta_node, str(item[0]), str(item[1]), str(item[2]), str(item[3]))

    # lock it
    ix.cmds.LockItems([meta_node.get_full_name()])


# ------------------------------------------------------------------------------
def save_snapshot():
    """
    Saves a snapshot of the current clarisse scene alongside the location where
    the actual scene itself lives.
    """

    name = ix.application.get_current_project_filename()
    if name:
        ix.application.save_project_snapshot(name)
        return True
    return False


# ------------------------------------------------------------------------------
def is_dirty():
    """
    If the scene needs to be saved, return True

    :return: True if the scene has changes that need to be saved.
    """

    if ix.is_gui_application():
        return str(ix.application.get_top_window().get_title()).endswith("*")
    return True


# ------------------------------------------------------------------------------
def get_current_project_file_name(return_full_path=True):
    """
    Returns the current project's full name (including path if fullPath is True)

    :param return_full_path: Whether to include the full path, or just the
           project name.

    :return: Either the name of the project file or the full path to the project
             file (depending on whether return_full_path is True or not).
    """

    path = ix.application.get_current_project_filename()
    if return_full_path:
        return path
    else:
        return os.path.split(path)[1]


# ------------------------------------------------------------------------------
def set_custom_attr(item,
                    section,
                    key,
                    value,
                    attr_type="string"):
    """
    Adds a custom attribute to the passed node. The custom attribute will be in
    the section defined by 'section'. The type is assumed to be string unless
    otherwise specified. If, for example, a color needs to be passed, then it
    should be passed as a list or tuple of length 3. Other multi-value values
    should be passed in the same manner. Returns the attribute added.

    :param item: Node on which to set the custom attribute
    :param section: Section in which to place the custom attribute
    :param key: Name of the attribute
    :param value: Value of the attribute
    :param attr_type: Type of the attribute

    :return: A clarisse attribute object
    """

    # Convert the attrType to all lowercase
    attr_type = attr_type.lower()

    if attr_type == "bool" or attr_type == "boolean":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_BOOL,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_DEFAULT,
                                  section)
        value = str(value)
        if value.upper() in ["TRUE", "T", "YES", "Y", "1", "ON"]:
            attr.set_bool(True)
        else:
            attr.set_bool(False)

    elif attr_type == "long" or attr_type == "integer":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_LONG,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_DEFAULT,
                                  section)
        attr.set_long(int(value))

    elif attr_type == "double":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_DEFAULT,
                                  section)
        attr.set_long(float(value))

    elif attr_type == "string":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_STRING,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_DEFAULT,
                                  section)
        attr.set_string(str(value))

    elif attr_type == "reference":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_REFERENCE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_DEFAULT,
                                  section)
        attr.set_object(value)

    elif attr_type == "percentage":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_PERCENTAGE,
                                  section)
        attr.set_double(float(value))

    elif attr_type == "distance":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_DISTANCE,
                                  section)
        attr.set_double(float(value))

    elif attr_type == "angle":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_ANGLE,
                                  section)
        attr.set_double(float(value))

    elif attr_type == "scale":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_SCALE,
                                  section)
        attr.set_double(float(value))

    elif attr_type == "frame":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_LONG,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_FRAME,
                                  section)
        attr.set_long(int(value))

    elif attr_type == "subframe":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_SUBFRAME,
                                  section)
        attr.set_double(float(value))

    elif attr_type == "l":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_L,
                                  section)
        attr.set_double(float(value))

    elif attr_type == "la":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_LA,
                                  section)
        attr.set_value_count(2)
        attr.set_double(float(value[0]), 0)
        attr.set_double(float(value[1]), 1)

    elif attr_type == "rgb":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_RGB,
                                  section)
        attr.set_value_count(3)
        attr.set_double(float(value[0]), 0)
        attr.set_double(float(value[1]), 1)
        attr.set_double(float(value[2]), 2)

    elif attr_type == "rgba":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_RGBA,
                                  section)
        attr.set_value_count(4)
        attr.set_double(float(value[0]), 0)
        attr.set_double(float(value[1]), 1)
        attr.set_double(float(value[2]), 2)
        attr.set_double(float(value[3]), 3)

    elif attr_type == "filein":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_FILE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_FILENAME_OPEN,
                                  section)
        attr.set_string(value)

    elif attr_type == "fileout":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_FILE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_FILENAME_SAVE,
                                  section)
        attr.set_string(value)

    elif attr_type == "pixel":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_PIXEL,
                                  section)
        attr.set_double(float(value))

    elif attr_type == "subpixel":
        attr = item.add_attribute(key,
                                  ix.api.OfAttr.TYPE_DOUBLE,
                                  ix.api.OfAttr.CONTAINER_SINGLE,
                                  ix.api.OfAttr.VISUAL_HINT_SUBPIXEL,
                                  section)
        attr.set_double(float(value))

    else:

        raise TypeError("attrType not a legal type.")

    return attr
