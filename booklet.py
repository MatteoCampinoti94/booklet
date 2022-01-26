from pathlib import Path
from typing import TypeVar

from PyPDF2.pdf import PageObject
from PyPDF2.pdf import PdfFileReader
from PyPDF2.pdf import PdfFileWriter
from click import Path as ClickPath
from click import argument
from click import command
from click import help_option
from click import option

T = TypeVar("T")


def read_pages(file: Path) -> list[PageObject | None]:
    reader: PdfFileReader = PdfFileReader(str(file))
    pages: list[PageObject | None] = [reader.getPage(n) for n in range(reader.getNumPages())]
    pages.extend([None] * (4 - p) if (p := len(pages) % 4) else [])
    return pages


def arrange_pages(pages: list[T], double_sided: bool = False) -> list[T]:
    pages_formatted: list[T | None]
    if double_sided:
        pages_formatted = [page for p in range(0, len(pages) // 2, 2)
                           for page in (pages[-(p + 1)], pages[p], pages[p + 1], pages[-(p + 2)])]
    else:
        pages_formatted = [page for p in range(0, len(pages), 2)
                           for page in (pages[-(p + 1)], pages[p])]
    return pages_formatted


def join_pages(pages: list[PageObject | None]) -> list[PageObject]:
    pages_join: list[PageObject] = []
    for p in range(0, len(pages), 2):
        page1, page2 = pages[p], pages[p + 1]
        if page1 is None and page2 is None:
            pages_join.append(PageObject.createBlankPage(None, 0, 0))
            continue
        page1 = page1 if page1 is not None else PageObject.createBlankPage(None, 1, 1)
        page2 = page2 if page2 is not None else PageObject.createBlankPage(None, 1, 1)
        new_page: PageObject = PageObject.createBlankPage(None,
                                                          max(page1.mediaBox.getHeight(), page2.mediaBox.getHeight()),
                                                          max(page1.mediaBox.getWidth(), page2.mediaBox.getWidth()))
        if page1:
            page1.rotateClockwise(90)
            page1.scaleBy(float(page1.mediaBox.getWidth() / page1.mediaBox.getHeight()))
            new_page.mergeTranslatedPage(page1, 0, 0)
        if page2:
            page2.rotateClockwise(90)
            page2.scaleBy(float(page2.mediaBox.getWidth() / page2.mediaBox.getHeight()))
            new_page.mergeTranslatedPage(page2, new_page.mediaBox.getWidth() - page2.mediaBox.getWidth(), 0)
        pages_join.append(new_page)
    return pages_join


def split_pages(pages: list[PageObject], joined: bool) -> tuple[list[PageObject], list[PageObject]]:
    return [page for p in range(0, len(pages), 2) for page in pages[p:p + 2 - joined]], \
           [page for p in range(1, len(pages), 2) for page in pages[p:p + 2 - joined]]


def write_pages(file: Path, pages: list[PageObject]):
    writer: PdfFileWriter = PdfFileWriter()
    for page in pages:
        writer.addPage(page) if page is not None else writer.addBlankPage(0, 0)

    with file.open("wb") as f:
        writer.write(f)


@command("booklet", no_args_is_help=True)
@argument("infile", metavar="IN", type=ClickPath(exists=True, dir_okay=False, path_type=Path))
@argument("outfile", metavar="OUT", type=ClickPath(exists=False, dir_okay=False, path_type=Path))
@option("--cover-page", type=ClickPath(exists=True, dir_okay=False, path_type=Path), required=None, default=None,
        help="Prefix cover page to generated booklet")
@option("--print-pattern", is_flag=True, default=False, help="Print pages pattern")
@option("--double-sided", is_flag=True, default=False, help="Generate booklet to be printed on both sides")
@option("--join-pages", "join_pages_", is_flag=True, default=False, help="Join pages")
@option("--split-pages", "split_pages_", is_flag=True, default=False, help="Split pages into print sides")
@help_option("-h", "--help")
def main(infile: Path, outfile: Path, cover_page: Path | None, print_pattern: bool, double_sided: bool,
         join_pages_: bool, split_pages_: bool):
    pages: list[PageObject] = read_pages(infile)
    pages = arrange_pages(pages, double_sided)
    if print_pattern:
        print(arrange_pages(list(range(1, len(pages) + 1)), double_sided))
    if join_pages_:
        pages = join_pages(pages)
    if cover_page:
        cover: PageObject = read_pages(cover_page)[0]
        pages.insert(0, cover)
        if double_sided:
            pages.insert(1, PageObject.createBlankPage(None, float(cover.mediaBox.getWidth()),
                                                       float(cover.mediaBox.getHeight())))
    if split_pages_:
        recto, verso = split_pages(pages, join_pages_)
        write_pages(outfile.with_name(f"recto - {outfile.name}"), recto)
        write_pages(outfile.with_name(f"verso - {outfile.name}"), verso)
    else:
        write_pages(outfile, pages)


if __name__ == '__main__':
    main()
