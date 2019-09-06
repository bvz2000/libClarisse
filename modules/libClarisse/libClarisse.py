import os.path
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


# --------------------------------------------------------------------------------------------------
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


# --------------------------------------------------------------------------------------------------
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
