%rebase _layout **locals()
Adding/changing value at {{node_path}}:

<form action="{{ request.fullpath }}" method="post">
    {{! form.render() }}
    <input type="submit" value="Send">
</form>