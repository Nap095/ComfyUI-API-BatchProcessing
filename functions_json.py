import json
from pathlib import Path



def get_node_block(workflow, block_name, node_id, attr_name, list_index=None):
    """Retourne la valeur de l'attribut d'un noeud dans un bloc.

    Args:
      workflow (dict): structure JSON entière.
      block_name (str): par exemple 'nodes'.
      node_id (int): ID du nœud à récupérer.
      attr_name (str): nom de l'attribut à lire, ex. 'widgets_values'.
      list_index (int|None): index si l'attribut est une liste.

    Return:
      valeur de l'attribut, ou None si impossible.
    """
    if not isinstance(workflow, dict):
        raise ValueError("workflow doit être un dict")

    block = workflow.get(block_name)
    if not isinstance(block, list):
        raise ValueError(f"{block_name} doit être une liste")

    node = next((n for n in block if n.get("id") == node_id), None)
    if node is None:
        raise ValueError(f"Noeud id={node_id} non trouvé dans {block_name}")

    if attr_name not in node:
        raise ValueError(f"Attribut '{attr_name}' absent du nœud id={node_id}")

    value = node[attr_name]
    if list_index is not None:
        if isinstance(list_index, int):
            if not isinstance(value, list):
                raise ValueError(f"Attribut '{attr_name}' n'est pas une liste")
            if not (0 <= list_index < len(value)):
                raise IndexError(f"list_index {list_index} hors plage")
            return value[list_index]
        else:
            if not isinstance(value, dict):
                raise ValueError(f"Attribut '{attr_name}' n'est pas un dict")
            return value.get(list_index)

    return value


def set_node_block(workflow, block_name, node_id, attr_name, new_value, index_or_key=None):
    """Modifie un attribut d'un nœud dans un bloc et retourne workflow mis à jour."""
    if not isinstance(workflow, dict):
        raise ValueError("workflow doit être un dict")

    block = workflow.get(block_name)
    if not isinstance(block, list):
        raise ValueError(f"{block_name} doit être une liste")

    node = next((n for n in block if str(n.get("id")) == str(node_id)), None)
    if node is None:
        raise ValueError(f"Noeud id={node_id} non trouvé dans {block_name}")

    if attr_name not in node:
        raise ValueError(f"Attribut '{attr_name}' absent du nœud id={node_id}")

    if index_or_key is not None:
        if isinstance(index_or_key, int):
            attr_value = node[attr_name]
            if not isinstance(attr_value, list):
                raise ValueError(f"Attribut '{attr_name}' n'est pas une liste")
            if not (0 <= index_or_key < len(attr_value)):
                raise IndexError(f"index {index_or_key} hors plage")
            attr_value[index_or_key] = new_value
            node[attr_name] = attr_value
        else:
            # Assume dict
            if not isinstance(node[attr_name], dict):
                raise ValueError(f"Attribut '{attr_name}' n'est pas un dict")
            node[attr_name][index_or_key] = new_value
    else:
        node[attr_name] = new_value

    # Mise à jour du bloc dans workflow
    workflow[block_name] = block
    return workflow


def main():
    source_path = Path(r"F:\Logiciels\AI\ComfyUI_windows_portable\ComfyUI\user\default\workflows\wkf-ZImage-Lora.json")
    if not source_path.exists():
        print(f"Fichier introuvable : {source_path}")
        return

    with source_path.open("r", encoding="utf-8") as f:
        workflow = json.load(f)

    # Exemples d'utilisation
    valeur_lue = get_node_block(workflow, "nodes", 6, "widgets_values", list_index=0)
    print("Valeur lue (widgets_values[0]) :", valeur_lue)

    workflow = set_node_block(workflow, "nodes", 6, "widgets_values", "paysage de mer", list_index=0)
    workflow = set_node_block(workflow, "nodes", 13, "widgets_values", 1111, list_index=0)
    workflow = set_node_block(workflow, "nodes", 13, "widgets_values", 111, list_index=1)
    workflow = set_node_block(workflow, "nodes", 13, "widgets_values", 2, list_index=2)
    print("Valeur modifiée, première entrée du tableau mise à jour")

    out_path = Path(r"c:\temp\read_json.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f_out:
        json.dump(workflow, f_out, ensure_ascii=False, indent=2)

    print(f"Fichier de sortie sauvegardé : {out_path}")


if __name__ == "__main__":
    main()
