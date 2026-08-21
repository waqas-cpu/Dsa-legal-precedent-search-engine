import json
from typing import List
from ingestion.schema import CaseDocument

def get_mock_corpus() -> List[CaseDocument]:
    mock_data = [
        {
            "doc_id": "plessy-v-ferguson-1896",
            "case_name": "Plessy v. Ferguson",
            "citation": "163 U.S. 537",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1896-05-18",
            "judges": ["Brown, J.", "Harlan, J."],
            "opinion_text": "We consider the underlying fallacy of the plaintiff's argument to consist in the assumption that the enforced separation of the two races stamps the colored race with a badge of inferiority. If this be so, it is not by reason of anything found in the act, but solely because the colored race chooses to put that construction upon it. Separate but equal laws do not abridge the Fourteenth Amendment's guarantee of equal protection under the law.",
            "headnotes": ["Separate but equal accommodations for white and colored railroad passengers are constitutional."],
            "citations_out": [],
            "practice_areas": ["constitutional-law", "civil-rights"],
            "treatment_signals": {
                "overruled_by": ["brown-v-board-of-education-1954"]
            }
        },
        {
            "doc_id": "brown-v-board-of-education-1954",
            "case_name": "Brown v. Board of Education",
            "citation": "347 U.S. 483",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1954-05-17",
            "judges": ["Warren, C.J."],
            "opinion_text": "We conclude that in the field of public education the doctrine of 'separate but equal' has no place. Separate educational facilities are inherently unequal. Therefore, we hold that the plaintiffs and others similarly situated for whom the actions have been brought are, by reason of the segregation complained of, deprived of the equal protection of the laws guaranteed by the Fourteenth Amendment. This opinion directly overrules the segregationist holding of Plessy v. Ferguson.",
            "headnotes": ["Segregation of children in public schools solely on the basis of race deprives children of minority groups of equal educational opportunities."],
            "citations_out": ["plessy-v-ferguson-1896"],
            "practice_areas": ["constitutional-law", "civil-rights", "education"],
            "treatment_signals": {
                "followed_by": ["loving-v-virginia-1967", "doe-v-state-school-dist-2015"]
            }
        },
        {
            "doc_id": "loving-v-virginia-1967",
            "case_name": "Loving v. Virginia",
            "citation": "388 U.S. 1",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1967-06-12",
            "judges": ["Warren, C.J."],
            "opinion_text": "Marriage is one of the 'basic civil rights of man,' fundamental to our very existence and survival. To deny this fundamental freedom on so unsupportable a basis as the racial classifications embodied in these statutes, classifications so directly subversive of the principle of equality at the heart of the Fourteenth Amendment, is surely to deprive all the State's citizens of liberty without due process of law. Equal protection requires the elimination of racial segregation in marriage. We follow the segregation-banning precedent of Brown v. Board of Education.",
            "headnotes": ["Virginia's statutory scheme to prevent marriages between persons solely on the basis of racial classifications violates the Fourteenth Amendment."],
            "citations_out": ["brown-v-board-of-education-1954"],
            "practice_areas": ["constitutional-law", "civil-rights", "family-law"],
            "treatment_signals": {}
        },
        {
            "doc_id": "escobedo-v-illinois-1964",
            "case_name": "Escobedo v. Illinois",
            "citation": "378 U.S. 478",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1964-06-22",
            "judges": ["Goldberg, J."],
            "opinion_text": "We hold that when the investigation is no longer a general inquiry into an unsolved crime but has begun to focus on a particular suspect, the suspect has been taken into police custody, the police carry out a process of interrogations that lends itself to eliciting incriminating statements, the suspect has requested and been denied an opportunity to consult with his lawyer, and the police have not effectively warned him of his absolute constitutional right to remain silent, the accused has been denied the Assistance of Counsel under the Sixth Amendment.",
            "headnotes": ["Where police investigation focuses on a suspect in custody and interrogation aims to elicit a confession, counsel must be permitted."],
            "citations_out": [],
            "practice_areas": ["criminal-procedure", "constitutional-law"],
            "treatment_signals": {
                "distinguished_by": ["miranda-v-arizona-1966"]
            }
        },
        {
            "doc_id": "gideon-v-wainwright-1963",
            "case_name": "Gideon v. Wainwright",
            "citation": "372 U.S. 335",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1963-03-18",
            "judges": ["Black, J."],
            "opinion_text": "The right of one charged with crime to counsel may not be deemed fundamental and essential to fair trials in some countries, but it is in ours. From the very beginning, our state and national constitutions and laws have laid great emphasis on procedural and substantive safeguards designed to assure fair trials before impartial tribunals in which every defendant stands equal before the law. In our adversary system of criminal justice, any person haled into court, who is too poor to hire a lawyer, cannot be assured a fair trial unless counsel is provided for him.",
            "headnotes": ["The Sixth Amendment's guarantee of counsel is a fundamental right essential to a fair trial, applicable to states via the Fourteenth Amendment."],
            "citations_out": [],
            "practice_areas": ["criminal-procedure", "constitutional-law"],
            "treatment_signals": {
                "followed_by": ["miranda-v-arizona-1966"]
            }
        },
        {
            "doc_id": "miranda-v-arizona-1966",
            "case_name": "Miranda v. Arizona",
            "citation": "384 U.S. 436",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1966-06-13",
            "judges": ["Warren, C.J."],
            "opinion_text": "Prior to any questioning, the person must be warned that he has a right to remain silent, that any statement he does make may be used as evidence against him, and that he has a right to the presence of an attorney, either retained or appointed. The defendant may waive effectuation of these rights, provided the waiver is made voluntarily, knowingly and intelligently. We follow the procedural safeguards and right to counsel of Gideon v. Wainwright and distinguish the narrower custody ruling of Escobedo v. Illinois. Miranda warnings are mandatory for custodial interrogation.",
            "headnotes": ["Statements obtained from custodial interrogation are inadmissible unless procedural safeguards securing privilege against self-incrimination are used."],
            "citations_out": ["gideon-v-wainwright-1963", "escobedo-v-illinois-1964"],
            "practice_areas": ["criminal-procedure", "constitutional-law"],
            "treatment_signals": {
                "followed_by": ["harris-v-new-york-1971", "state-v-jones-2018"]
            }
        },
        {
            "doc_id": "harris-v-new-york-1971",
            "case_name": "Harris v. New York",
            "citation": "401 U.S. 222",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1971-02-24",
            "judges": ["Burger, C.J."],
            "opinion_text": "Some comments in the Miranda opinion can indeed be read as indicating a bar to any use of statements obtained in violation of Miranda. But that was not the holding. Miranda barred the prosecution from making its case-in-chief using such statements. It does not follow that statements inadmissible in its case-in-chief are barred for all purposes, provided of course that the trustworthiness of the evidence satisfies legal standards. The shield provided by Miranda cannot be perverted into a license to use perjury by way of a defense. We follow Miranda but distinguish its application regarding impeachment.",
            "headnotes": ["Statements obtained in violation of Miranda may be used to impeach a defendant's credibility if they are trustworthy."],
            "citations_out": ["miranda-v-arizona-1966"],
            "practice_areas": ["criminal-procedure", "constitutional-law", "evidence"],
            "treatment_signals": {}
        },
        {
            "doc_id": "marbury-v-madison-1803",
            "case_name": "Marbury v. Madison",
            "citation": "5 U.S. 137",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1803-02-24",
            "judges": ["Marshall, C.J."],
            "opinion_text": "It is emphatically the province and duty of the judicial department to say what the law is. Those who apply the rule to particular cases, must of necessity expound and interpret that rule. If two laws conflict with each other, the courts must decide on the operation of each. So if a law be in opposition to the constitution; if both the law and the constitution apply to a particular case, so that the court must either decide that case conformably to the law, disregarding the constitution; or conformably to the constitution, disregarding the law; the court must determine which of these conflicting rules governs the case. This is the very essence of judicial review under Article III.",
            "headnotes": ["The Supreme Court has the power of judicial review to declare acts of Congress unconstitutional."],
            "citations_out": [],
            "practice_areas": ["constitutional-law", "judicial-review"],
            "treatment_signals": {
                "followed_by": ["cooper-v-aaron-1958", "loper-bright-v-raimondo-2024"]
            }
        },
        {
            "doc_id": "cooper-v-aaron-1958",
            "case_name": "Cooper v. Aaron",
            "citation": "358 U.S. 1",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1958-09-29",
            "judges": ["Warren, C.J."],
            "opinion_text": "The constitutional rights of children not to be discriminated against in school admission on grounds of race or color declared by this Court in the Brown case can neither be nullified openly and directly by state legislators or state executive or judicial officers, nor nullified indirectly by them through evasive schemes for segregation. Article VI of the Constitution makes the Constitution the supreme Law of the Land. As declared in Marbury v. Madison, it is the province of the judiciary to say what the law is. The holdings of the Supreme Court bind the States.",
            "headnotes": ["State opposition to desegregation does not suspend the obligation to comply with desegregation rulings, which are binding under the Supremacy Clause."],
            "citations_out": ["marbury-v-madison-1803", "brown-v-board-of-education-1954"],
            "practice_areas": ["constitutional-law", "civil-rights"],
            "treatment_signals": {}
        },
        {
            "doc_id": "roe-v-wade-1973",
            "case_name": "Roe v. Wade",
            "citation": "410 U.S. 113",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1973-01-22",
            "judges": ["Blackmun, J."],
            "opinion_text": "This right of privacy, whether it be founded in the Fourteenth Amendment's concept of personal liberty and restrictions upon state action, as we feel it is, or, as the District Court determined, in the Ninth Amendment's reservation of rights to the people, is broad enough to encompass a woman's decision whether or not to terminate her pregnancy. The detriment that the State would impose upon the pregnant woman by denying this choice altogether is apparent. We hold that a pregnant woman has a constitutional right of privacy under the due process clause.",
            "headnotes": ["The constitutional right to privacy under the Fourteenth Amendment's Due Process Clause encompasses a woman's decision to have an abortion."],
            "citations_out": [],
            "practice_areas": ["constitutional-law", "privacy", "healthcare"],
            "treatment_signals": {
                "overruled_by": ["dobbs-v-jackson-womens-health-2022"]
            }
        },
        {
            "doc_id": "dobbs-v-jackson-womens-health-2022",
            "case_name": "Dobbs v. Jackson Women's Health Organization",
            "citation": "597 U.S. 215",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "2022-06-24",
            "judges": ["Alito, J."],
            "opinion_text": "We hold that Roe and Casey must be overruled. The Constitution makes no reference to abortion, and no such right is implicitly protected by any constitutional provision, including the one on which the defenders of Roe and Casey now chiefly rely—the Due Process Clause of the Fourteenth Amendment. That provision has been held to guarantee some rights that are not mentioned in the Constitution, but any such right must be 'deeply rooted in this Nation's history and tradition' and 'implicit in the concept of ordered liberty.' Abortion does not meet this criteria. We explicitly overrule the constitutional privacy holding in Roe v. Wade.",
            "headnotes": ["The Constitution does not confer a right to abortion; Roe and Casey are overruled, and the authority to regulate abortion is returned to the people and their elected representatives."],
            "citations_out": ["roe-v-wade-1973"],
            "practice_areas": ["constitutional-law", "privacy", "healthcare"],
            "treatment_signals": {}
        },
        {
            "doc_id": "chevron-v-nrdc-1984",
            "case_name": "Chevron U.S.A., Inc. v. Natural Resources Defense Council, Inc.",
            "citation": "467 U.S. 837",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "1984-06-25",
            "judges": ["Stevens, J."],
            "opinion_text": "When a court reviews an agency's construction of the statute which it administers, it is confronted with two questions. First, always, is the question whether Congress has directly spoken to the precise question at issue. If the intent of Congress is clear, that is the end of the matter. If, however, the court determines Congress has not directly addressed the precise question at issue, the court does not simply impose its own construction on the statute. Rather, if the statute is silent or ambiguous with respect to the specific issue, the question for the court is whether the agency's answer is based on a permissible construction of the statute. This is the doctrine of Chevron deference to administrative agency interpretation of ambiguous laws.",
            "headnotes": ["Where a statute is silent or ambiguous, courts must defer to an agency's reasonable interpretation of the statute."],
            "citations_out": [],
            "practice_areas": ["administrative-law", "environmental-law"],
            "treatment_signals": {
                "overruled_by": ["loper-bright-v-raimondo-2024"]
            }
        },
        {
            "doc_id": "loper-bright-v-raimondo-2024",
            "case_name": "Loper Bright Enterprises v. Raimondo",
            "citation": "603 U.S. ___",
            "court": "U.S. Supreme Court",
            "court_level": 1,
            "jurisdiction": "US-Federal",
            "date_decided": "2024-06-28",
            "judges": ["Roberts, C.J."],
            "opinion_text": "The Administrative Procedure Act requires courts to exercise their independent judgment in deciding whether an agency has acted within its statutory authority, and courts may not defer to an agency's interpretation of the law simply because a statute is ambiguous. We hold that the Administrative Procedure Act incorporates the traditional rule of judicial review—that courts, not agencies, must decide all questions of law. Chevron deference is incompatible with the APA and is hereby overruled. We follow the principle of judicial supremacy established in Marbury v. Madison.",
            "headnotes": ["The Administrative Procedure Act requires courts to decide all relevant questions of law and interpret statutory provisions, overruling Chevron deference."],
            "citations_out": ["chevron-v-nrdc-1984", "marbury-v-madison-1803"],
            "practice_areas": ["administrative-law", "constitutional-law"],
            "treatment_signals": {}
        },
        {
            "doc_id": "doe-v-state-school-dist-2015",
            "case_name": "Doe v. State School District",
            "citation": "789 F.3d 123",
            "court": "U.S. Court of Appeals for the Ninth Circuit",
            "court_level": 2,
            "jurisdiction": "US-Federal",
            "date_decided": "2015-04-10",
            "judges": ["Thomas, J."],
            "opinion_text": "Under Brown v. Board of Education, equal protection guarantees that state public schools cannot segregate pupils on arbitrary bases. While the school district argues that its placement policies do not constitute racial segregation, we find that the structural disadvantage created by this layout violates the Fourteenth Amendment's Equal Protection Clause. We follow the principles of desegregation established in Brown.",
            "headnotes": ["School assignment policies that operate to segment student bodies unlawfully under Fourteenth Amendment are unconstitutional."],
            "citations_out": ["brown-v-board-of-education-1954"],
            "practice_areas": ["civil-rights", "education"],
            "treatment_signals": {}
        },
        {
            "doc_id": "state-v-jones-2018",
            "case_name": "State v. Jones",
            "citation": "123 F.Supp.3d 456",
            "court": "U.S. District Court for the Southern District of New York",
            "court_level": 3,
            "jurisdiction": "US-Federal",
            "date_decided": "2018-09-05",
            "judges": ["Rakoff, J."],
            "opinion_text": "The defendant moves to suppress statements made during his arrest. Because officers failed to read him his Miranda warnings prior to custodial interrogation, any statements obtained are inadmissible in the government's case-in-chief. Under Miranda v. Arizona, warnings are an absolute prerequisite to admissibility. Under Harris v. New York, however, should the defendant take the stand, these statements may be used for impeachment. Motion to suppress is granted in part and denied in part.",
            "headnotes": ["Custodial interrogation statements made without Miranda warnings are inadmissible in case-in-chief, but admissible for impeachment if trustworthy."],
            "citations_out": ["miranda-v-arizona-1966", "harris-v-new-york-1971"],
            "practice_areas": ["criminal-procedure", "constitutional-law", "evidence"],
            "treatment_signals": {}
        }
    ]
    return [CaseDocument(**doc) for doc in mock_data]

def load_corpus_from_json(file_path: str) -> List[CaseDocument]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [CaseDocument(**doc) for doc in data]
