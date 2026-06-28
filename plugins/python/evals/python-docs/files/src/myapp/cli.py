import click


@click.group()
def cli() -> None:
    """myapp command-line interface."""


@cli.command()
@click.option("--port", default=8080, help="Port to listen on.")
def serve(port: int) -> None:
    """Run the HTTP server."""
    click.echo(f"serving on {port}")
