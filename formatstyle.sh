# see pyproject.toml for settings
echo "Sorting imports"
isort custom_components/todo_list_voice_management tests

echo "Formatting files"
black custom_components/todo_list_voice_management tests

echo "Formatting json files"
for i in custom_components/todo_list_voice_management/*.json custom_components/todo_list_voice_management/translations/*.json
do
    echo "    $i"
    python -m json.tool "$i" > /dev/null || exit
    python -m json.tool "$i" > "$i.new"
    if diff "$i" "$i.new" >/dev/null 2>/dev/null
    then
        cat "$i.new" > "$i"
    fi
    rm "$i.new"
done

echo "Checking sentence files"
for i in custom_components/todo_list_voice_management/sentences/*.yaml
do
    echo "    $i"
    python -c 'import sys, yaml; yaml.safe_load(open(sys.argv[1], encoding="utf-8"))' "$i" || exit
done

echo "flake8 style and complexity checks"
flake8 custom_components/**/*.py || exit

echo "pydocstyle checks"
pydocstyle -v custom_components/todo_list_voice_management tests || exit

echo "pylint checks"
pylint custom_components/todo_list_voice_management || exit

echo "bandit security checks"
bandit -r -q custom_components/todo_list_voice_management || exit
