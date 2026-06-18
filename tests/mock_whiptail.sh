#!/bin/bash
# Mock whiptail for non-interactive testing
# Always return success and echo the first item for menus/inputboxes

args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
    case "${args[i]}" in
        --yesno) exit 0 ;;
        --inputbox) echo "pytask" >&2; exit 0 ;;
        --menu)
            # Find the start of menu items (after height width menu-height)
            # Whiptail menu syntax: --menu text height width menu-height [tag item]...
            # We just want to return the first tag.
            # tag is args[i+5]
            echo "${args[i+5]}" >&2
            exit 0
            ;;
    esac
done
exit 0
