import typer

JSON = typer.Option(
    False,
    "--json",
    help="Print the result as JSON on stdout instead of a rendered view",
)
