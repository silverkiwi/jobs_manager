export function loadJobDetails() {
  const materialField = document.getElementById("material_gauge_quantity");
  const descriptionField = document.getElementById("job_description");

  if (!materialField || !descriptionField) {
    throw new Error(
      "Required fields material_gauge_quantity and/or job_description are missing from page",
    );
  }

  const autoExpand = (field) => {
    field.style.height = "inherit";
    const computed = window.getComputedStyle(field);
    const height = [
      "border-top-width",
      "padding-top",
      "padding-bottom",
      "border-bottom-width",
    ].reduce(
      (sum, prop) => sum + parseInt(computed.getPropertyValue(prop), 10),
      field.scrollHeight,
    );
    field.style.height = `${height}px`;
  };

  [materialField, descriptionField].forEach((field) => {
    field.addEventListener("input", () => autoExpand(field));
    autoExpand(field);
  });
}
