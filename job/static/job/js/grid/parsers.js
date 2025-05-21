export function currencyFormatter(params) {
  if (params.value === undefined) {
    // console.error('currencyFormatter error: value is undefined for the following params:', params);
    return "$0.00"; // Return a fallback value so the grid doesn't break
  }
  return (
    "$" +
    params.value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

export function numberParser(params) {
  return Number(params.newValue);
}
