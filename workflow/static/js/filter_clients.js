function filterClients() {
  const searchTerm = document.getElementById("search").value.toLowerCase();
  const clientTableBody = document.getElementById("client-table-body");

  if (!clientTableBody) return;

  clientTableBody.querySelectorAll(".client-row").forEach((row) => {
    const name = row.dataset.name || "";
    const email = row.dataset.email || "";
    const phone = row.dataset.phone || "";
    const address = row.dataset.address || "";
    const accountCustomer = row.dataset.accountCustomer || "";

    const combinedText = [name, email, phone, address, accountCustomer]
      .join(" ")
      .toLowerCase();

    row.style.display = combinedText.includes(searchTerm) ? "" : "none";
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("search");
  if (searchInput) {
    searchInput.addEventListener("input", filterClients);
  }
});
