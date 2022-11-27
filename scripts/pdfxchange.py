import sys
from os.path import basename

from fitz import Document


def clean_annotations() -> None:
    for link in g_page.get_links():
        if (
            link["uri"]
            == "https://www.tracker-software.com/product/pdf-xchange-editor"
        ):
            g_page.delete_link(link)


def get_xobjects() -> list[str]:
    def is_water_mark(xobject: tuple[int]) -> bool:
        xref = xobject[0]
        return g_pdf.xref_is_stream(
            xref
        ) and b"Click to BUY NOW!" in g_pdf.xref_stream(xref)

    xobjects = g_pdf.get_page_xobjects(g_page.number)
    return [x[1] for x in xobjects if is_water_mark(x)]


def clean_xobjects(xobjects: list[str]) -> None:
    def delete_xobject(xobject_name: str) -> None:
        stream: bytes = g_page.read_contents()
        while (loc := stream.find(f"/{xobject_name} Do".encode())) != -1:
            if (loc_start := stream.rfind(b"/Artifact", 0, loc)) == -1:
                return
            if (loc_end := stream.find(b"EMC", loc)) == -1:
                return
            stream = stream[:loc_start] + stream[loc_end + 3 :]

        g_pdf.update_stream(g_page.get_contents()[0], stream)

    for xobject_name in xobjects:
        delete_xobject(xobject_name)


def clean_page() -> None:
    g_page.clean_contents()  # concatenates the content streams
    clean_annotations()
    xobjects = get_xobjects()
    clean_xobjects(xobjects)


if len(sys.argv) < 3:
    sys.exit(
        f"Not enough arguments.\n"
        f"Usage:\n"
        f"\t{basename(sys.argv[0])} <input.pdf> <output.pdf>"
    )

g_pdf = Document(sys.argv[1])

for g_page in g_pdf.pages():
    clean_page()

g_pdf.save(sys.argv[2], clean=True, deflate=True)
