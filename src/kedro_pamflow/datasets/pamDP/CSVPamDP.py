from pathlib import PurePosixPath
from typing import Any, Dict, List
import fsspec
from kedro.io.core import get_filepath_str, get_protocol_and_path
import os
from kedro_datasets.pandas import CSVDataset
from kedro.io.core import (
    PROTOCOL_DELIMITER,
    AbstractVersionedDataset,
    DatasetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)
import pandas as pd


class CSVPamDP(CSVDataset):
    def __init__(
        self,
        pamdp_columns,
        required_dictionary,
        schema_dictionary,
        unique_dictionary,
        filepath: str,
        timezone: str = "UTC",
        date_columns: List[str] | None = None,
        enum_dictionary: Dict[str, Any] | None = None,
        load_args: Dict[str, Any] | None = None,
        save_args: Dict[str, Any] | None = None,
        version: Version | None = None,
        credentials: Dict[str, Any] | None = None,
        fs_args: Dict[str, Any] | None = None,
        metadata: Dict[str, Any] | None = None,
    ):
        super().__init__(
            filepath=filepath,
            load_args=load_args,
            save_args=save_args,
            version=version,
            credentials=credentials,
            fs_args=fs_args,
            metadata=metadata,
        )

        self.pamdp_columns = pamdp_columns
        self.required_dictionary = required_dictionary
        self.schema_dictionary = schema_dictionary
        self.unique_dictionary = unique_dictionary
        self.enum_dictionary = enum_dictionary
        self.date_columns = date_columns
        self.timezone = timezone

    def _load(self):
        df = super()._load()
        # 1. Check column names & order
        if set(df.columns) != set(self.pamdp_columns):
            if set(df.columns).issubset(set(self.pamdp_columns)):
                raise ValueError(
                    f"Missing columns for pamDP.Media format: \n list of missing columns {set(self.pamdp_columns) - set(df.columns)}"
                )
            elif set(self.pamdp_columns).issubset(df.columns):
                raise ValueError(
                    f"Extra columns for pamDP.Media format: \n The following columns are not part of pamDP.Media format {set(df.columns) - set(self.pamdp_columns)}"
                )
            else:
                raise ValueError(f"""Column mismatch. There are extra and missing columns for pamDP.Media format. \n Expected columns: {self.pamdp_columns} 
                \n Missing columns: {set(self.pamdp_columns) - set(df.columns)} 
                \n Extra Columns{set(df.columns) - set(self.pamdp_columns)}""")

        # 2. Check column types
        try:
            df.astype(self.schema_dictionary)
        except ValueError as err:
            raise err

        # 3. Check mandatory columns for nulls
        for col, mandatory in self.required_dictionary.items():
            if df[col].isnull().any() and mandatory:
                raise ValueError(f"Mandatory column {col} contains null values.")

        # 4. Check unique constraints
        for col, unique_constraint in self.unique_dictionary.items():
            if df[col].duplicated().any() and unique_constraint:
                raise ValueError(
                    f"Column {col} has duplicate values but should be unique."
                )
        # 5. Check categorical data constraints
        if self.enum_dictionary is not None:
            for col, enum_values in self.enum_dictionary.items():
                if not set(df[df[col].notna()][col].unique()).issubset(
                    set(enum_values)
                ):
                    raise ValueError(f"""Expected unique values for  {col}: {enum_values}. \n
                                            The values {set(df[df[col].notna()][col].unique()) - set(enum_values)}
                                            are not allowed for this field. 
                        """)
        #6. ISO 8601 date format 
        if self.date_columns is not None:
            for col in self.date_columns:
                df[col]=pd.to_datetime(df[col]).apply(lambda x: x.isoformat())

        return df[self.pamdp_columns]

    def _save(self, df):
        # 1. Check column names & order
        if set(df.columns) != set(self.pamdp_columns):
            if set(df.columns).issubset(set(self.pamdp_columns)):
                raise ValueError(
                    f"Missing columns for pamDP.Media format: \n list of missing columns {set(self.pamdp_columns) - set(df.columns)}"
                )
            elif set(self.pamdp_columns).issubset(df.columns):
                raise ValueError(
                    f"Extra columns for pamDP.Media format: \n The following columns are not part of pamDP.Media format {set(df.columns) - set(self.pamdp_columns)}"
                )
            else:
                raise ValueError(f"""Column mismatch. There are extra and missing columns for pamDP.Media format. \n Expected columns: {self.pamdp_columns} 
                \n Missing columns: {set(self.pamdp_columns) - set(df.columns)} 
                \n Extra Columns{set(df.columns) - set(self.pamdp_columns)}""")

        # 2. Check column types
        try:
            df.astype(self.schema_dictionary)
        except ValueError as err:
            raise err

        # 3. Check mandatory columns for nulls
        for col, mandatory in self.required_dictionary.items():
            if df[col].isnull().any() and mandatory:
                raise ValueError(f"Mandatory column {col} contains null values.")

        # 4. Check unique constraints
        for col, unique_constraint in self.unique_dictionary.items():
            if df[col].duplicated().any() and unique_constraint:
                raise ValueError(
                    f"Column {col} has duplicate values but should be unique."
                )
        # 5. ISO 8601 date format 
        if self.date_columns is not None:
            for col in self.date_columns:
                df[col]=pd.to_datetime(df[col]).apply(lambda x: x.isoformat())
        
        super()._save(df[self.pamdp_columns])
