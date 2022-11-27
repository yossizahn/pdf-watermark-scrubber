import sys
from os.path import basename
from typing import Any

from fitz import Document, Page


def clean_annotations(page: Page) -> None:
    for link in page.get_links():
        if link["uri"] == "http://www.iceni.com/unlock-pro.htm":
            page.delete_link(link)


def get_xobjects(pdf: Document, page: Page) -> list[str]:
    def is_water_mark(xobject: tuple[int, Any, int, Any]) -> bool:
        (xref, _, invoker, _) = xobject
        return invoker == 0 and pdf.xref_get_key(xref, "IceniWatermark") == (
            "name",
            "/IceniWatermark",
        )

    xobjects = pdf.get_page_xobjects(page.number)
    return [
        x[1] for x in xobjects if is_water_mark(x)
    ]  # x[1] holds the object's name


def clean_xobjects(pdf: Document, page: Page, xobjects: list[str]) -> None:
    def delete_xobject(xobject_name: str) -> None:
        stream: bytes = page.read_contents()
        while (loc := stream.find(f"/{xobject_name} Do".encode())) != -1:
            if (loc_start := stream.rfind(b"q\n", 0, loc)) == -1:
                return
            if (loc_end := stream.find(b"\nQ", loc)) == -1:
                return
            stream = stream[:loc_start] + stream[loc_end + 3 :]

        pdf.update_stream(page.get_contents()[0], stream)

    for xobject_name in xobjects:
        delete_xobject(xobject_name)


def clean_page(pdf: Document, page: Page) -> None:
    page.clean_contents()  # concatenates the content streams
    clean_annotations(page)
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

    for page in pdf.pages():
        clean_page(pdf, page)

    pdf.save(sys.argv[2], clean=True, deflate=True)


if __name__ == "__main__":
    main()
