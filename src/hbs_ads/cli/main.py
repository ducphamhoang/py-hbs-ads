from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from hbs_ads.app.bootstrap import build_app
from hbs_ads.cli.parser import build_parser
from hbs_ads.cli.renderers import render_error, render_result
from hbs_ads.core.errors import AppError

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()
    try:
        namespace = parser.parse_args(args_list)
    except SystemExit as exc:
        return int(exc.code)
    app = build_app(workspace_override=namespace.workspace, output_mode=namespace.output)
    handler = getattr(namespace, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    try:
        result = handler(namespace, app)
    except AppError as exc:
        render_error(
            exc,
            output_mode=namespace.output,
            command=_command_name(namespace),
            workspace=namespace.workspace,
        )
        return exc.exit_code
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        render_error(
            AppError(f"Unexpected error: {exc.__class__.__name__}: {exc}", exit_code=1),
            output_mode=namespace.output,
            command=_command_name(namespace),
            workspace=namespace.workspace,
        )
        return 1

    result.output_mode = namespace.output
    render_result(
        result,
        command=_command_name(namespace),
        workspace=namespace.workspace,
    )
    return 0


def _command_name(namespace: object) -> str:
    parts: list[str] = []
    for attribute in ("command", "action", "cron_action"):
        value = getattr(namespace, attribute, "")
        if value:
            parts.append(str(value))
    return " ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
