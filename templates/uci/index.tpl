%rebase _layout **locals()
%def render_buttons(element):
    %if not element.final:
        %if element.tag == "section":
        <a href="{{ url("uci_create", node=element.path, operation="add-option") }}" title="Add option"><i class="icon-add"></i></a>
        <a href="{{ url("uci_create", node=element.path, operation="add-list") }}" title="Add list"><i class="icon-add-list"></i></a>
        %else:
        <a href="{{ url("uci_create", node=element.path, operation="add") }}" title="Add value"><i class="icon-add"></i></a>
        %end
    %end
    %if element.tag == "option" or element.tag == "value":
        <a href="{{ url("uci_edit", node=element.path) }}" title="Edit"><i class="icon-edit"></i></a>
    %end
    %if element.tag != "config":
        <a href="{{ url("uci_remove", node=element.path) }}"><i class="icon-remove"></i></a>
    %end
        <a href="{{ url("uci_debug", node=element.path) }}" title="Debug"><i class="icon-debug"></i></a>
%end
%def treenode(element, node_path, depth=0):
    <li>
    %if not element.final or depth == 0:
        <input type="checkbox" id="{{ element.path }}" {{! " checked=\"checked\"" if node_path and len(node_path) > depth and node_path[depth] == element.key else "" }}><label for="{{element.path}}">{{element}}</label>
        %render_buttons(element)
    %end
    <ul>
    %for child in element.children:
        %if not child.final:
            %treenode(child, node_path, depth + 1)
        %else:
            <li>{{child}}
                %render_buttons(child)
            </li>
        %end
    %end
    </ul>
    </li>
%end

%############################## PAGE ITSELF STARTS HERE ############################################
<h1>Foris</h1>
<h2>about:config</h2>

%if tree:
    <div class="treeview">
    <ul>
    %for config in tree.children:
        %treenode(config, node_path)
    %end
    </ul>
    </div>
%end