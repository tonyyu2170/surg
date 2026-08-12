import pytest

from surg.acquisition.entsoe_parse import parse_response

LOAD_XML = """<?xml version="1.0" encoding="utf-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
  <mRID>a8a2c94ba7d64c70b081e99e40a9a750</mRID>
  <type>A65</type>
  <TimeSeries>
    <mRID>1</mRID>
    <outBiddingZone_Domain.mRID codingScheme="A01">10YIE-1001A00010</outBiddingZone_Domain.mRID>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-08T00:00Z</start><end>2024-01-08T02:00Z</end></timeInterval>
      <resolution>PT30M</resolution>
      <Point><position>1</position><quantity>3635.66</quantity></Point>
      <Point><position>3</position><quantity>3469.86</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""

PRICE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <mRID>a1027a4c3c4847488119f1b2ad80263e</mRID>
  <TimeSeries>
    <mRID>1</mRID>
    <in_Domain.mRID codingScheme="A01">10YNL----------L</in_Domain.mRID>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-07T23:00Z</start><end>2024-01-08T01:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><price.amount>87.02</price.amount></Point>
      <Point><position>2</position><price.amount>81.5</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
"""

ACK_XML = """<?xml version="1.0" encoding="utf-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:8:0">
  <Reason>
    <code>999</code>
    <text>No matching data found for Data item ACTUAL_TOTAL_LOAD_R3 [6.1.A].</text>
  </Reason>
</Acknowledgement_MarketDocument>
"""

NO_VALUE_XML = """<?xml version="1.0" encoding="utf-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
  <TimeSeries>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-08T00:00Z</start><end>2024-01-08T02:00Z</end></timeInterval>
      <resolution>PT30M</resolution>
      <Point><position>1</position><quantity>100.0</quantity></Point>
      <Point><position>2</position></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""

EMPTY_TEXT_XML = """<?xml version="1.0" encoding="utf-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
  <TimeSeries>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-08T00:00Z</start><end>2024-01-08T01:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity/></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""

MULTI_PERIOD_XML = """<?xml version="1.0" encoding="utf-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
  <TimeSeries>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-08T00:00Z</start><end>2024-01-08T01:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>10.0</quantity></Point>
    </Period>
    <Period>
      <timeInterval><start>2024-01-08T01:00Z</start><end>2024-01-08T02:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>20.0</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""


def test_parses_load_document_into_period_records():
    result = parse_response(LOAD_XML)
    assert result.kind == "data"
    assert len(result.periods) == 1
    p = result.periods[0]
    assert p["doc_start"] == "2024-01-08T00:00Z"
    assert p["doc_end"] == "2024-01-08T02:00Z"
    assert p["resolution"] == "PT30M"
    assert p["curve_type"] == "A03"
    assert p["points"] == [(1, 3635.66), (3, 3469.86)]


def test_parses_price_document_using_price_amount():
    result = parse_response(PRICE_XML)
    assert result.kind == "data"
    assert result.periods[0]["points"] == [(1, 87.02), (2, 81.5)]
    assert result.periods[0]["resolution"] == "PT60M"


def test_acknowledgement_is_no_data_not_success():
    # HTTP 200 + reason 999 is emptiness, not data. Status code alone lies.
    result = parse_response(ACK_XML)
    assert result.kind == "no_data"
    assert result.reason_code == "999"
    assert "No matching data" in result.reason_text
    assert result.periods == []


def test_multiple_periods_in_one_timeseries_are_kept_separate():
    # Expansion is per Period; merging them would corrupt the dense span.
    result = parse_response(MULTI_PERIOD_XML)
    assert len(result.periods) == 2
    assert result.periods[0]["points"] == [(1, 10.0)]
    assert result.periods[1]["points"] == [(1, 20.0)]


def test_unparseable_body_raises():
    with pytest.raises(ValueError, match="could not parse"):
        parse_response("this is not xml")


def test_point_without_a_value_raises_rather_than_vanishing():
    # A dropped point is invisible under A03: the slot forward-fills and the
    # resulting sparsity looks like ordinary compression.
    with pytest.raises(ValueError, match="Point missing position or value"):
        parse_response(NO_VALUE_XML)


def test_empty_value_text_raises_value_error_not_type_error():
    # Pins the module's "malformed input -> ValueError" convention.
    with pytest.raises(ValueError, match="Point missing position or value"):
        parse_response(EMPTY_TEXT_XML)
