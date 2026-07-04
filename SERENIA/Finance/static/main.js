// Alert for transaction form in home page

const debit = document.querySelector("#debit");
const credit = document.querySelector("#credit");
const particular = document.querySelector("#particular");
const amount = document.querySelector("#amount");
const transactionbtn = document.querySelector("#add-transaction-btn");

if (transactionbtn) {
    transactionbtn.onclick = function () {
        if (debit.value == "" || credit.value == "" || particular.value == "" || amount.value == "") {
            alert("Input field is empty");
            return false;
        }

        else if (debit.value === credit.value) {
            alert("Debit and credit entry must be different");
            return false;
        }
    }
}


// Change select options based on select value in type of account in add-account page

const type = document.querySelector("#type")
const subtype = document.querySelector("#subtype")

if (type) {
    type.addEventListener("change", function() {
        if (type.value === "NCA") {
            subtype.innerHTML = '<option value="ppe">Property, plant and equipment</option><option value="investments">Investments</option><option value="intangibles">Intangibles</option>'
        }

        else if (type.value === "CA") {
            subtype.innerHTML = '<option value="inventories">Inventories</option><option value="receivables">Trade receivables</option><option value="cash">Cash and cash equivalents</option>';
        }

        else if (type.value === "NCL") {
            subtype.innerHTML = '<option value="long-borrowings">Long-term borrowings</option><option value="deferred-tax">Deferred tax</option>';
        }

        else if (type.value === "CL") {
            subtype.innerHTML = '<option value="payables">Trade and other payables</option><option value="short-borrowings">Short-term borrowings</option><option value="tax-payable">Current tax payable</option><option value="provisions">Short-term provisions</option>';
        }

        else if (type.value === "EQT") {
            subtype.innerHTML = '<option value="capital">Capital</option><option value="other-equity">Other components of equity</option>';
        }

        else if (type.value === "INC") {
            subtype.innerHTML = '<option value="sales">Sales</option><option value="investment-income">Investment income</option><option value="other-income">Other income</option>';
        }

        else if (type.value === "EXP") {
            subtype.innerHTML = '<option value="cost-of-sales">Cost of sales</option><option value="distribution-costs">Distribution costs</option><option value="admin-exp">Administrative expenses</option><option value="finance-costs">Finance costs</option><option value="tax-exp">Income tax expense</option>';
        }

        else {
            subtype.innerHTML = ""
        }
    });
}

// Prompt user to confirm when clicking delete account

const dlt = document.querySelector("#delete-account-link")

if (dlt) {
    dlt.onclick = function() {
        if(!confirm("Are you sure to delete this account? This action cannot be undone")) {
            return false;
        }
    }
}

// Data table

$(document).ready( function () {
    $("#table_id").DataTable();
} );
