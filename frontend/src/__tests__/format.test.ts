import { csvField, datasetNameFromFile, formatCell, formatMs, toCsv } from "../format";

describe("formatCell", () => {
  it("shows NULL for missing values", () => {
    expect(formatCell(null)).toBe("NULL");
  });
  it("groups thousands and trims long decimals", () => {
    expect(formatCell(8866000)).toBe("8,866,000");
    expect(formatCell(3.14159265)).toBe("3.1416");
  });
  it("serialises lists", () => {
    expect(formatCell([1, 2])).toBe("[1,2]");
  });
});

describe("csv export", () => {
  it("quotes fields with commas, quotes and newlines", () => {
    expect(csvField("plain")).toBe("plain");
    expect(csvField("a,b")).toBe('"a,b"');
    expect(csvField('say "hi"')).toBe('"say ""hi"""');
    expect(csvField("two\nlines")).toBe('"two\nlines"');
    expect(csvField(null)).toBe("");
  });
  it("builds a CRLF separated document with a header", () => {
    expect(toCsv(["city", "pop"], [["London", 1], ["King's Lynn, Norfolk", null]])).toBe(
      'city,pop\r\nLondon,1\r\n"King\'s Lynn, Norfolk",\r\n',
    );
  });
});

describe("datasetNameFromFile", () => {
  it("makes a safe table name", () => {
    expect(datasetNameFromFile("Bike Trips 2026.csv")).toBe("bike_trips_2026");
    expect(datasetNameFromFile("2026-sales.csv")).toBe("_2026_sales");
    expect(datasetNameFromFile("???.csv")).toBe("dataset");
  });
});

describe("formatMs", () => {
  it("switches to seconds above one second", () => {
    expect(formatMs(12.345)).toBe("12.3 ms");
    expect(formatMs(2500)).toBe("2.50 s");
  });
});
