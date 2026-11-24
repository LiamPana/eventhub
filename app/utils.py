from datetime import datetime, timezone


def utcnow():
    """Data/ora UTC "naive" (senza tzinfo), coerente con le colonne DateTime di MySQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def register_filters(app):
    @app.template_filter("dt")
    def format_datetime(value):
        return value.strftime("%d/%m/%Y %H:%M") if value else "-"

    @app.template_filter("money")
    def format_money(value):
        return f"€ {value:.2f}"
