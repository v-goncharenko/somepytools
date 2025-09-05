# duplicates in sheets formula: =COUNTIF(A:A, A1) > 1

from typing import Any, Union

import gspread
import polars as pl
from google.auth import default
from google.colab import auth
from oauth2client.client import GoogleCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


def auth_gspread() -> gspread.client.Client:
    auth.authenticate_user()
    creds, _ = default()
    gc = gspread.authorize(creds)
    return gc


def auth_pydrive(dummy_call: bool = False) -> GoogleDrive:
    """
    Args:
        dummy_call: needed if you want to perform non PyDrive2 native operations with service object
    """
    auth.authenticate_user()
    gauth = GoogleAuth()
    gauth.credentials = GoogleCredentials.get_application_default()
    drive = GoogleDrive(gauth)

    if dummy_call:
        file_list = drive.ListFile(  # noqa: F841
            {"q": "'root' in parents and trashed=false"}
        ).GetList()

    return drive


def sheets(gc, spreadsheet_id: str) -> dict[str, Any]:
    """"""
    spreadsheet = gc.open_by_key(spreadsheet_id)
    return {ws.title: ws for ws in spreadsheet}


def worksheet2pl(worksheet):
    all_vals = worksheet.get(
        major_dimension=gspread.utils.Dimension.cols,
        value_render_option=gspread.utils.ValueRenderOption.unformatted,
        date_time_render_option=gspread.utils.DateTimeOption.formatted_string,
        pad_values=True,
    )

    df = pl.DataFrame(all_vals, strict=False)
    df = df.rename(df.head(1).to_dicts().pop())
    df = df.with_row_index()
    df = df.filter(pl.col("index") != 0)
    return df


def number2letters(q: int) -> str:
    """Helper function to convert number of column to its index, like 10 -> 'A'"""
    q = q - 1
    result = ""

    while q >= 0:
        remain = q % 26
        result = chr(remain + 65) + result
        q = q // 26 - 1

    return result


def colrow2range(col: int, row: int) -> str:
    """Helper function converting coordinates into sheets range string representation"""
    return number2letters(col) + str(row)


def write_table(
    ws,
    table: Union[list, pl.DataFrame],
    left: int = 1,
    top: int = 1,
    *,
    with_headers: bool = True,
):
    """Updates the google spreadsheet with given table

    Args:
        ws: gspread.models.Worksheet object
        rows: a table (list of lists) or polars data frame (will be converted internally)
        left: the number of the first column in the target document (beginning with 1)
        top: the number of first row in the target document (beginning with 1)
        with_headers: in case of rows as pl.DataFrame to take headers or not
    """
    if isinstance(table, pl.DataFrame):
        columns = table.columns
        table = table.rows()
        if with_headers:
            table.insert(0, columns)

    # number of rows and columns
    num_lines, num_columns = len(table), len(table[0])

    # selection of the range that will be updated
    top_left = colrow2range(left, top)
    bot_right = colrow2range(left + num_columns - 1, top + num_lines - 1)
    cell_list = ws.range(f"{top_left}:{bot_right}")

    # modifying the values in the range

    for cell in cell_list:
        cell.value = table[cell.row - top][cell.col - left]

    # update in batch
    ws.update_cells(cell_list)


def copy_drive_file(drive, source: str, dest_dir: str, dest_fname: str):
    """Copy Google Drive file

    Args:
        source: id of the file to be copyed
        dest_dir: id of directory to put copy to
        dest_fname: name of restulting document
    """
    return (
        drive.auth.service.files()
        .copy(
            fileId=source,
            body={
                "parents": [{"kind": "drive#fileLink", "id": dest_dir}],
                "title": dest_fname,
            },
        )
        .execute()
    )
