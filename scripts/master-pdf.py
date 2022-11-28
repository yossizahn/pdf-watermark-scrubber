import sys
from os.path import basename
from typing import Any

from fitz import Document, Page


def get_xobjects(pdf: Document, page: Page) -> list[str]:
    def is_water_mark(xobject: tuple[int, Any, int, Any]) -> bool:
        (xref, _, invoker, _) = xobject
        return pdf.xref_get_key(
            xref, "PieceInfo/ADBE_CompoundType/Private"
        ) == (
            "name",
            "/WatermarkDemo",
        )

    xobjects = pdf.get_page_xobjects(page.number)
    return [
        x[1] for x in xobjects if is_water_mark(x)
    ]  # x[1] holds the object's name


def clean_xobjects(pdf: Document, page: Page, xobjects: list[str]) -> None:
    def delete_xobject(xobject_name: str) -> None:
        do_str = f"/{xobject_name} Do".encode()
        begin = b"q\n"
        end = b"\nQ"
        stream: bytes = page.read_contents()
        while (loc := stream.find(do_str)) != -1:
            if (loc_start := stream.rfind(begin, 0, loc)) == -1:
                return
            if (loc_end := stream.find(end, loc)) == -1:
                return
            stream = stream[:loc_start] + stream[loc_end + len(end) :]

        pdf.update_stream(page.get_contents()[0], stream)

    for xobject_name in xobjects:
        delete_xobject(xobject_name)


def clean_page(pdf: Document, page: Page) -> None:
    xobjects = get_xobjects(pdf, page)
    clean_xobjects(pdf, page, xobjects)


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(
            f"Not enough arguments.\n"
            f"Usage:\n"
            f"\t{basename(sys.argv[0])} <input.pdf> <output.pdf>"
        )

    pdf = Document(sys.argv[1])

    for p in pdf.pages():
        page: Page = p
        page.clean_contents()
        clean_page(pdf, page)

    pdf.save(sys.argv[2])


if __name__ == "__main__":
    main()
