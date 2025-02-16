RESPONSE_CODES = {

    "ERR_SOMETHING_WENT_WRONG": {
        "code": "E0000",
        "message": "Something went wrong."
    },

    "ERR_NOT_OWNER": {
        "code": "E1001",
        "message": "Only the user who created this transaction can modify it."
    },
    "ERR_NON_GROUP_MEMBER": {
        "code": "E1002",
        "message": "All participants must be members of the group."
    },
    "ERR_GROUP_REQUIRED": {
        "code": "E1003",
        "message": "Please provide a group for group transactions."
    },
    "ERR_FRIENDS_REQUIRED": {
        "code": "E1004",
        "message": "The payer and participants must be friends."
    },
    "ERR_SPLIT_MISMATCH": {
        "code": "E1005",
        "message": "The split amounts do not match the total transaction amount."
    },
    "ERR_INVALID_SPLIT_DETAILS": {
        "code": "E1006",
        "message": "Each entry in split_details must contain a valid 'user' (integer) and 'amount' (positive integer or float)."
    },
    "ERR_SPLIT_DETAILS_REQUIRED": {
        "code": "E1007",
        "message": "Split details must be provided."
    },
    "ERR_TRANSACTION_NOT_FOUND": {
        "code": "E1008",
        "message": "Transaction not found."
    },
    "ERR_PARTICIPANT_NOT_FOUND": {
        "code": "E1009",
        "message": "Participant not found."
    },
    "ERR_DUPLICATE_USER_IN_SPLIT": {
        "code": "E1010",
        "message": "Duplicate Participant Found in Split"
    },
    "ERR_PAYER_NOT_IN_SPLIT": {
        "code": "E1011",
        "message": "Payer must be in the split"
    },
    "ERR_NOT_ALL_GROUP_MEMBERS_INCLUDED ": {
        "code": "E1012",
        "message": "All group participant must be in the split"
    },

    "SUCCESS_TRANSACTION_CREATED": {
        "code": "S2000",
        "message": "Transaction created successfully."
    },

    "SUCCESS_TRANSACTION_MODIFIED": {
        "code": "S2001",
        "message": "Transaction modified successfully."
    }
}
