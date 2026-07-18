"""The study catalog: metadata and LINKS ONLY. The app never hosts or fetches the datasets;
users download them from CIBMTR under CIBMTR's Terms & Conditions.

In production this would be a small database or a versioned YAML file; hardcoded here for the
Milestone-1 study so the pipeline has a concrete catalog entry to run against.
"""
from __future__ import annotations

from pydantic import BaseModel


class StudyCatalogEntry(BaseModel):
    study_id: str
    cibmtr_study_number: str
    working_committee: str
    title: str
    citation: str
    doi: str | None = None
    pmid: str | None = None
    manuscript_url: str
    dataset_download_url: str      # user fetches this themselves, under T&C
    data_dictionary_url: str
    terms_url: str = "https://cibmtr.org/CIBMTR/Resources/Data-Sharing"
    note: str = (
        "Download the dataset yourself from CIBMTR and accept CIBMTR's Terms & Conditions. "
        "This app stores only metadata and links; it does not host or redistribute the data."
    )


CATALOG: dict[str, StudyCatalogEntry] = {
    "P-5297": StudyCatalogEntry(
        study_id="P-5297",
        cibmtr_study_number="MM18-03a",
        working_committee="Plasma Cell Disorders",
        title=("Age no bar: A CIBMTR analysis of elderly patients undergoing autologous "
               "hematopoietic cell transplantation for multiple myeloma"),
        citation="Munshi PN et al. Cancer. 2020;126(23):5077-5087.",
        doi="10.1002/cncr.33171",
        pmid="32965680",
        manuscript_url="https://cibmtr.org/Manuscript/a020h00001GktXqAAJ/P-5297",
        dataset_download_url=(
            "https://cibmtr.org/ReferenceCenter/PubList/PubDsDownload/Documents/P-5297.zip"),
        data_dictionary_url=(
            "https://cibmtr.org/ReferenceCenter/PubList/PubDsDownload/Documents/"
            "DataDictionaryFiles/P-5297/MM18-03---data-dictionary.xlsx"),
    ),
    "P-5306": StudyCatalogEntry(
        study_id="P-5306",
        cibmtr_study_number="CV20-02a",
        working_committee="Severe Aplastic Anemia",
        title=("Hematopoietic cell transplantation with cryopreserved grafts for severe "
               "aplastic anemia"),
        citation="Eapen M, et al. Biol Blood Marrow Transplant. 2020;26(9):e161-e166.",
        doi="10.1016/j.bbmt.2020.04.027",
        pmid="32389803",
        manuscript_url="https://cibmtr.org/Manuscript/a020h00001F142GAAR/P-5306",
        dataset_download_url=(
            "https://cibmtr.org/ReferenceCenter/PubList/PubDsDownload/Documents/P-5306.zip"),
        data_dictionary_url=(
            "https://cibmtr.org/ReferenceCenter/PubList/PubDsDownload/Documents/"
            "DataDictionaryFiles/P-5306/CV2002a-Cryopreserved-SAA-data-dictionary.rtf"),
        terms_url="https://cibmtr.org/Files/Publicly-Available-Datasets/TermsAndConditions.pdf",
    ),
}


def get_entry(study_id: str) -> StudyCatalogEntry:
    if study_id not in CATALOG:
        raise KeyError(f"study '{study_id}' not in catalog")
    return CATALOG[study_id]
