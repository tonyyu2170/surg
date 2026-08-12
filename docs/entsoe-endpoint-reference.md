# ENTSO-E REST API — Per-Endpoint Parameter Reference

Generated 2026-08-12 from the Postman collection "Transparency Platform
Restful API", `https://documenter.getpostman.com/api/collections/7009892/2s93JtP3F6`
(the browsable view is `https://documenter.getpostman.com/view/7009892/2s93JtP3F6`).

Companion to `entsoe-api-constraints.md`. 77 endpoints, 8 folders.
`[M]` = mandatory, `[O]` = optional, per ENTSO-E's own annotations.
Parameter values shown are the collection's worked examples.

Regenerate with:

```bash
curl -s https://documenter.getpostman.com/api/collections/7009892/2s93JtP3F6 -o collection.json
```

then walk `collection.item[].item[].request.urlObject.query[]`.

---

### [Market] 12.1.E Implicit and Flow-based Allocations - Congestion Income
METHOD: GET
URL: {{baseUrl}}?documentType=A25&businessType=B10&contract_MarketAgreement.Type=A01&out_Domain=10YAT-APG------L&in_Domain=10YAT-APG------L&periodStart=202308232200&periodEnd=202308242200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A25   :: [M] A25 = Allocation results
    - businessType = B10   :: [M] B10 = Congestion income
    - contract_MarketAgreement.Type = A01   :: [M] A01 = Daily; A07 = Intraday
    - out_Domain = 10YAT-APG------L   :: [M] EIC code of a Border (or Bidding Zone for Flow Based Allocations)
    - in_Domain = 10YAT-APG------L   :: [M] EIC code of a Border (or Bidding Zone for Flow Based Allocations) - same as out_Domain
    - periodStart = 202308232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Market] 12.1.B Total Nominated Capacity
METHOD: GET
URL: {{baseUrl}}?documentType=A26&businessType=B08&out_Domain=10YGB----------A&in_Domain=10YBE----------2&periodStart=202308202200&periodEnd=202308212200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A26   :: [M] A26 = Capacity document
    - businessType = B08   :: [M] B08 = Total nominated capacity
    - out_Domain = 10YGB----------A   :: [M] EIC code of a Control Area or Bidding Zone
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area or Bidding Zone
    - periodStart = 202308202200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308212200   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Market] 11.1 Implicit Allocations - Offered Transfer Capacity
METHOD: GET
URL: {{baseUrl}}?documentType=A31&auction.Type=A01&contract_MarketAgreement.Type=A01&out_Domain=10YDK-1--------W&in_Domain=10Y1001A1001A82H&periodStart=202212312300&periodEnd=202301012300
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A31   :: [M] A31 = Agreed capacity
    - auction.Type = A01   :: [M] A01 = Implicit
    - contract_MarketAgreement.Type = A01   :: [M] A01 = Day ahead; A07 = Intraday
    - out_Domain = 10YDK-1--------W   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - in_Domain = 10Y1001A1001A82H   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - periodStart = 202212312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202301012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - Update_DateAndOrTime = 20230313123900   :: [O] For Offered Capacity Evolution can be quried with datetime in numeric. For example 20210803113900000 for evolution update date time 03.08.2021 13:39:00.000
    - ClassificationSequence_AttributeInstanceComponent.Position = 1   :: [O] Integer
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Market] 12.1.H Transfer Capacities Allocated with Third Countries [12.1.H] (explicit)
METHOD: GET
URL: {{baseUrl}}?documentType=A94&auction.Type=A02&contract_MarketAgreement.Type=A07&out_Domain=10YFI-1--------U&in_Domain=10Y1001A1001A49F&periodStart=202308232200&periodEnd=202308242200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A94   :: [M] A94 = Non EU allocations
    - auction.Type = A02   :: [M] A02 = Explicit
    - contract_MarketAgreement.Type = A07   :: [M] A07 = Intraday; A01 = Daily; A02 = Weekly; A03 = Monthly; A08 = Quarterly; A04 = Yearly; A06 = Long Term
    - out_Domain = 10YFI-1--------U   :: [M] EIC code of a Control Area, Bidding Zone, Bidding Zone Aggregation
    - in_Domain = 10Y1001A1001A49F   :: [M] EIC code of a Control Area, Bidding Zone, Bidding Zone Aggregation
    - periodStart = 202308232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - auction.Category = A04   :: [O] A01 = Base; A02 = Peak; A03 = Off Peak; A04 = Hourly
    - classificationSequence_AttributeInstanceComponent.Position = 1   :: [O] Integer
    - curveType = A03   :: [O] A01 = Sequential fixed block (available only for contract_MarketAgreement.Type = A01 and A07); A03 = Variable sized blocks (default)

### [Market] 12.1.C Total Capacity Already Allocated
METHOD: GET
URL: {{baseUrl}}?documentType=A26&businessType=A29&contract_MarketAgreement.Type=A01&out_Domain=10YHR-HEP------M&in_Domain=10YBA-JPCC-----D&periodStart=202308242200&periodEnd=202308252200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A26   :: [M] A26 = Capacity Document
    - businessType = A29   :: [M] A29 = Already Allocated Capacity
    - contract_MarketAgreement.Type = A01   :: [M] A07 = Intraday; A01 = Daily; A02 = Weekly; A03 = Monthly; A08 = Quarterly; A04 = Yearly; A06 = Long Term
    - out_Domain = 10YHR-HEP------M   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - in_Domain = 10YBA-JPCC-----D   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - periodStart = 202308242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308252200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - auction.Category = A02   :: [O] A01 = Base; A02 = Peak; A03 = Off Peak; A04 = Hourly
    - curveType = A03   :: [O] A01 = Sequential fixed block (available only for contract_MarketAgreement.Type = A01 and A07); A03 = Variable sized blocks (default)

### [Market] 11.1.A Explicit Allocations - Offered Transfer Capacity
METHOD: GET
URL: {{baseUrl}}?documentType=A31&auction.Type=A02&contract_MarketAgreement.Type=A01&out_Domain=10YGB----------A&in_Domain=10YBE----------2&periodStart=202308152200&periodEnd=202308162200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A31   :: [M] A31 = Agreed capacity
    - auction.Type = A02   :: [M] A02 = Explicit
    - contract_MarketAgreement.Type = A01   :: [M] A07 = Intraday; A01 = Day ahead; A02 = Weekly; A03 = Monthly; A08 = Quarterly; A04 = Yearly; A06 = Long Term
    - out_Domain = 10YGB----------A   :: [M] EIC code of Control Area, Bidding Zone or Bidding Zone Aggregation
    - in_Domain = 10YBE----------2   :: [M] EIC code of Control Area, Bidding Zone or Bidding Zone Aggregation
    - periodStart = 202308152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - auction.Category = A04   :: [O] A01 = Base; A02 = Peak; A03 = Off Peak; A04 = Hourly
    - Update_DateAndOrTime = 20230313123900   :: [O] For Offered Capacity Evolution can be quried with datetime in numeric. For example 20210803113900000 for evolution update date time 03.08.2021 13:39:00.000
    - ClassificationSequence_AttributeInstanceComponent.Position = 1   :: [O] Integer
    - curveType = A03   :: [O] A01 = Sequential fixed block (available only for contract_MarketAgreement.Type = A01 and A07); A03 = Variable sized blocks (default)

### [Market] 12.1.A Explicit Allocations - Use of the Transfer Capacity
METHOD: GET
URL: {{baseUrl}}?documentType=A25&businessType=B05&contract_MarketAgreement.Type=A07&out_Domain=10YGB----------A&in_Domain=10YBE----------2&periodStart=202308152200&periodEnd=202308162200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A25   :: [M] A25 = Allocation result document
    - businessType = B05   :: [M] A43 = Requested capacity (without price); B05 = Capacity allocated (including price)
    - contract_MarketAgreement.Type = A07   :: [M] A07 = Intraday; A01 = Day ahead; A02 = Weekly; A03 = Monthly; A08 = Quarterly; A04 = Yearly; A06 = Long Term
    - out_Domain = 10YGB----------A   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - periodStart = 202308152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - Auction.Category = A04   :: [O] A01 = Base; A02 = Peak; A03 = Off Peak; A04 = Hourly
    - ClassificationSequence_AttributeInstanceComponent.Position = 1   :: [O] Integer
    - curveType = A03   :: [O] A01 = Sequential fixed block (available only for contract_MarketAgreement.Type = A01 and A07); A03 = Variable sized blocks (default)

### [Market] 12.1.A Explicit Allocations - Auction Revenue
METHOD: GET
URL: {{baseUrl}}?documentType=A25&businessType=B07&contract_MarketAgreement.Type=A01&out_Domain=10YHR-HEP------M&in_Domain=10YBA-JPCC-----D&periodStart=202308242200&periodEnd=202308252200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A25   :: [M] A25 = Allocation result document
    - businessType = B07   :: [M] B07 = Auction Revenue
    - contract_MarketAgreement.Type = A01   :: [M] A07 = Intraday; A01 = Daily; A02 = Weekly; A03 = Monthly; A08 = Quarterly; A04 = Yearly; A06 = Long Term
    - out_Domain = 10YHR-HEP------M   :: [M] EIC code of a Control Area, Bidding Zone or a Bidding Zone Aggregation
    - in_Domain = 10YBA-JPCC-----D   :: [M] EIC code of a Control Area, Bidding Zone or a Bidding Zone Aggregation
    - periodStart = 202308242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308252200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block (available only for contract_MarketAgreement.Type = A01 and A07); A03 = Variable sized blocks (default)

### [Market] 12.1.E Implicit Auction — Net Positions
METHOD: GET
URL: {{baseUrl}}?documentType=A25&businessType=B09&contract_MarketAgreement.Type=A07&out_Domain=10YBE----------2&in_Domain=10YBE----------2&periodStart=202308222200&periodEnd=202308232200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A25   :: [M] A25 = Allocation results
    - businessType = B09   :: [M] B09 = Net position
    - contract_MarketAgreement.Type = A07   :: [M] A01 = Daily; A05 = Total; A07 = Intraday
    - out_Domain = 10YBE----------2   :: [M] EIC code of a Bidding Zone or a Control Area
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Bidding Zone or a Control Area (must be same as out_Domain)
    - periodStart = 202308222200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curvetype = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Market] 11.1.B Flow Based Allocations
METHOD: GET
URL: {{baseUrl}}?documentType=B09&processType=A44&out_Domain=10YDOM-REGION-1V&in_Domain=10YDOM-REGION-1V&periodStart=201402032300&periodEnd=201402040500
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 1 instances contained in the ZIP response, split into several files within the response ZIP file.
    - documentType = B09   :: [M] B09 = Flow Based Domain Publication
    - processType = A44   :: [M] A43 = Day ahead; A44 = Intraday; A32 = Month-ahead; A33 = Year-ahead
    - out_Domain = 10YDOM-REGION-1V   :: [M] EIC code of a Region
    - in_Domain = 10YDOM-REGION-1V   :: [M] EIC code of a Region
    - periodStart = 201402032300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 201402040500   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000

### [Market] 11.1.B Flow Based Allocations Archives
METHOD: GET
URL: {{baseUrl}}?documentType=B09&processType=A32&out_Domain=10YDOM-REGION-1V&in_Domain=10YDOM-REGION-1V&periodStart=201812302300&periodEnd=201812312200&StorageType=archive
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 1 archive in the ZIP response.
    - documentType = B09   :: [M] B09 = Flow Based Domain Publication
    - processType = A32   :: [M] A43 = Day ahead; A44 = Intraday; A32 = Month-ahead; A33 = Year-ahead
    - out_Domain = 10YDOM-REGION-1V   :: [M] EIC code of a Region
    - in_Domain = 10YDOM-REGION-1V   :: [M] EIC code of a Region
    - periodStart = 201812302300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 201812312200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - StorageType = archive   :: [M] archive

### [Market] 11.1 Continuous Allocations - Offered Transfer Capacity
METHOD: GET
URL: {{baseUrl}}?DocumentType=A31&Auction.Type=A08&Out_Domain=10YBE----------2&In_Domain=10YNL----------L&PeriodStart=202405152200&PeriodEnd=202504162200&Contract_MarketAgreement.Type=A07
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - DocumentType = A31   :: [M] A31 = Agreed capacity; B33 = Published offered capacity
    - Auction.Type = A08   :: [M] A08 = Continuous
    - Out_Domain = 10YBE----------2   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - In_Domain = 10YNL----------L   :: [M] EIC code of a Control Area, Bidding Zone or Bidding Zone Aggregation
    - PeriodStart = 202405152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - PeriodEnd = 202504162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - Contract_MarketAgreement.Type = A07   :: [M] A07 = Intraday
    - Update_DateAndOrTime = 20240515123900   :: [O] For Offered Capacity Evolution can be quried with datetime in numeric. For example 20210803113900000 for evolution update date time 03.08.2021 13:39:00.000. If there is no OC evolution version with requested update_DateAndOrTime the system selects OC version valid in the given time (e.g., closest previous update_DateAndOrTime). The most recent publish OC version is provided in case the update_DateAndOrTime parameter is omitted. The most recent published OC version and intermediate OC versions is distinguished by document type: − Intermediate OC values: A31 − Most recent published OC values: B33
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Market] 12.1.D Energy Prices
METHOD: GET
URL: {{baseUrl}}?documentType=A44&periodStart=202407272200&periodEnd=202407282200&out_Domain=10YAT-APG------L&in_Domain=10YAT-APG------L
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A44   :: [M] Price Document
    - periodStart = 202407272200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202407282200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - out_Domain = 10YAT-APG------L   :: [M] EIC code of a Bidding Zone
    - in_Domain = 10YAT-APG------L   :: [M] EIC code of a Bidding Zone (must be same as out_Domain)
    - contract_MarketAgreement.type = A01   :: [O] A01 = Day-ahead ; A07 = Intraday
    - classificationSequence_AttributeInstanceComponent.position = 1   :: [O] Integer
    - offset = 0   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Load] 6.1.A Actual Total Load - SECURITY_TOKEN in header
METHOD: GET
URL: {{baseUrl}}?documentType=A65&processType=A16&outBiddingZone_Domain=10YCZ-CEPS-----N&periodStart=202303030000&periodEnd=202303060000
DESC: Request limit: Each request may cover a period of up to 1 year. Note : This is an example where the security token is included in the request header rather than in the query parameters.
    - documentType = A65   :: [M] A65 = System total load
    - processType = A16   :: [M] A16 = Realised
    - outBiddingZone_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202303030000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202303060000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)
    HDR SECURITY_TOKEN: {{apiKey}}  :: 

### [Load] 6.1.A Actual Total Load (Post)
METHOD: POST
URL: {{baseUrl}}
DESC: Request limit: Each request may cover a period of up to 1 year.
    HDR Content-Type: application/xml  :: 
    HDR SECURITY_TOKEN: {{apiKey}}  :: 
    BODY: <StatusRequest_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-5:statusrequestdocument:4:0"> <mRID>SampleCallToRestfulApi</mRID> <type>A59</type> <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID> <sender_MarketParticipant.marketRole.type>A07</sender_MarketParticipant.marketRole.type> <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID> <receiver_MarketParticipant.marketRole.type>A32</receiver_M

### [Load] 6.1.A Actual Total Load
METHOD: GET
URL: {{baseUrl}}?documentType=A65&processType=A16&outBiddingZone_Domain=10YCZ-CEPS-----N&periodStart=202303030000&periodEnd=202303060000
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A65   :: [M] A65 = System total load
    - processType = A16   :: [M] A16 = Realised
    - outBiddingZone_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202303030000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202303060000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Load] 6.1.B Day-ahead Total Load Forecast
METHOD: GET
URL: {{baseUrl}}?documentType=A65&processType=A01&outBiddingZone_Domain=10YCZ-CEPS-----N&periodStart=202308140000&periodEnd=202308170000
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A65   :: [M] A65 = System total load
    - processType = A01   :: [M] A01 = Day ahead
    - outBiddingZone_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202308140000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308170000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Load] 6.1.C Week-ahead Total Load Forecast
METHOD: GET
URL: {{baseUrl}}?documentType=A65&processType=A31&outBiddingZone_Domain=10YCZ-CEPS-----N&periodStart=202308132200&periodEnd=202308202200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A65   :: [M] A65 = System total load
    - processType = A31   :: [M] A31 = Week ahead
    - outBiddingZone_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202308132200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308202200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Load] 6.1.D Month-ahead Total Load Forecast
METHOD: GET
URL: {{baseUrl}}?documentType=A65&processType=A32&outBiddingZone_Domain=10YCZ-CEPS-----N&periodStart=202307022200&periodEnd=202308062200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A65   :: [M] A65 = System total load
    - processType = A32   :: [M] A32 = Month ahead
    - outBiddingZone_Domain = 10YCZ-CEPS-----N   :: [M] EIC of a Control Area, Bidding Zone or Country
    - periodStart = 202307022200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308062200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Load] 6.1.E Year-ahead Total Load Forecast
METHOD: GET
URL: {{baseUrl}}?documentType=A65&processType=A33&outBiddingZone_Domain=10YCZ-CEPS-----N&periodStart=202301012300&periodEnd=202312312300&curveType=A03
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A65   :: [M] A65 = System total load
    - processType = A33   :: [M] A33 = Year ahead
    - outBiddingZone_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202301012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Load] 8.1 Year-ahead Forecast Margin
METHOD: GET
URL: {{baseUrl}}?documentType=A70&processType=A33&outBiddingZone_Domain=10YCZ-CEPS-----N&periodStart=202212312300&periodEnd=202312312300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A70   :: [M] A70 = Load forecast margin
    - processType = A33   :: [M] A33 = Year ahead
    - outBiddingZone_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202212312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Generation] 14.1.A Installed Capacity per Production Type
METHOD: GET
URL: {{baseUrl}}?documentType=A68&processType=A33&in_Domain=10YBE----------2&periodStart=202212312300&periodEnd=202312312300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A68   :: [M] A68 = Installed generation per type
    - processType = A33   :: [M] A33 = Year ahead
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202212312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - PsrType = B01   :: [O] B01 = Biomass; B02 = Fossil Brown coal/Lignite; B03 = Fossil Coal-derived gas; B04 = Fossil Gas; B05 = Fossil Hard coal; B06 = Fossil Oil; B07 = Fossil Oil shale; B08 = Fossil Peat; B09 = Geothermal; B10 = Hydro Pumped Storage; B11 = Hydro Run-of-river and poundage; B12 = Hydro Water Reservoir; B13 = Marine; B14 = Nuclear; B15 = Other renewable; B16 = Solar; B17 = Waste; B18 = Wind Offshore; B19 = Wind Onshore; B20 = Other; B25 = Energy storage
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Generation] 16.1.D Water Reservoirs and Hydro Storage Plants
METHOD: GET
URL: {{baseUrl}}?documentType=A72&processType=A16&in_Domain=10YCA-BULGARIA-R&periodStart=202307092100&periodEnd=202307162100
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A72   :: [M] A72 = Reservoir filling information
    - processType = A16   :: [M] A16 = Realised
    - in_Domain = 10YCA-BULGARIA-R   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202307092100   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202307162100   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Generation] 16.1.B&C Actual Generation per Production Type
METHOD: GET
URL: {{baseUrl}}?documentType=A75&processType=A16&in_Domain=10Y1001A1001A83F&periodStart=202308152200&periodEnd=202308162200
DESC: Request limit : Each request may cover a period of up to 1 year. Response from API is same irrespective of querying for Document Types A74 - Wind & Solar & A75 - Actual Generation Per Type Time series with inBiddingZone_Domain attribute reflects Generation values while outBiddingZone_Domain reflects Consumption values.**
    - documentType = A75   :: [M] A75 = Actual generation per type (all production types); A74 = Wind and solar generation only
    - processType = A16   :: [M] A16 = Realised
    - in_Domain = 10Y1001A1001A83F   :: [M] Control Area, Bidding Zone, Country
    - periodStart = 202308152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - psrType = B01   :: [O] B01 = Biomass; B02 = Fossil Brown coal/Lignite; B03 = Fossil Coal-derived gas; B04 = Fossil Gas; B05 = Fossil Hard coal; B06 = Fossil Oil; B07 = Fossil Oil shale; B08 = Fossil Peat; B09 = Geothermal; B10 = Hydro Pumped Storage; B11 = Hydro Run-of-river and poundage; B12 = Hydro Water Reservoir; B13 = Marine; B14 = Nuclear; B15 = Other renewable; B16 = Solar; B17 = Waste; B18 = Wind Offshore; B19 = Wind Onshore; B20 = Other; B25 = Energy storage
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Generation] 16.1.A Actual Generation per Generation Unit
METHOD: GET
URL: {{baseUrl}}?documentType=A73&processType=A16&in_Domain=10YBE----------2&periodStart=202308152200&periodEnd=202308162200
DESC: Request limit: Each request may cover a period of up to 1 day. Important notes: Response from API is same irrespective of querying for Document Types A74 - Wind & Solar & A75 - Actual Generation Per Type Time series with inBiddingZone_Domain attribute reflects generation values while outBiddingZone_Domain reflects consumption values.
    - documentType = A73   :: [M] A73 = Actual generation
    - processType = A16   :: [M] A16 = Realised
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area
    - periodStart = 202308152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - PsrType = B14   :: [O] B01 = Biomass; B02 = Fossil Brown coal/Lignite; B03 = Fossil Coal-derived gas; B04 = Fossil Gas; B05 = Fossil Hard coal; B06 = Fossil Oil; B07 = Fossil Oil shale; B08 = Fossil Peat; B09 = Geothermal; B10 = Hydro Pumped Storage; B11 = Hydro Run-of-river and poundage; B12 = Hydro Water Reservoir; B13 = Marine; B14 = Nuclear; B15 = Other renewable; B16 = Solar; B17 = Waste; B18 = Wind Offshore; B19 = Wind Onshore; B20 = Other; B25 = Energy storage
    - RegisteredResource = 22WAMERCO000008L   :: [O] EIC Code of a Generation Unit
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Generation] 14.1.C Generation Forecast - Day ahead
METHOD: GET
URL: {{baseUrl}}?documentType=A71&processType=A01&in_Domain=10YBE----------2&periodStart=202308152200&periodEnd=202308162200
DESC: Request limit: Each request may cover a period of up to 1 year. Time series with inBiddingZone_Domain attribute reflects Generation values while outBiddingZone_Domain reflects Consumption values.
    - documentType = A71   :: [M] A71 = Generation forecast
    - processType = A01   :: [M] A01 = Day ahead
    - in_Domain = 10YBE----------2   :: [M] Control Area, Bidding Zone, Country
    - periodStart = 202308152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Generation] 14.1.D Generation Forecasts for Wind and Solar
METHOD: GET
URL: {{baseUrl}}?documentType=A69&processType=A01&in_Domain=10YBE----------2&periodStart=202308152200&periodEnd=202308162200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A69   :: [M] A69 = Wind and solar forecast
    - processType = A01   :: [M] A01 = Day ahead; A18 = Current; A40 = Intraday
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area, Bidding Zone or Country
    - periodStart = 202308152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - PsrType = B16   :: [O] B16 = Solar; B18 = Wind Offshore; B19 = Wind Onshore;
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Generation] 14.1.B Installed Capacity Per Production Unit
METHOD: GET
URL: {{baseUrl}}?documentType=A71&processType=A33&in_Domain=10YBE----------2&periodStart=202308010000&periodEnd=202308020000
DESC: 
    - documentType = A71   :: [M] A71 = Generation forecast
    - processType = A33   :: [M] A33 = Year ahead
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area or Bidding Zone
    - periodStart = 202308010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308020000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - PsrType = B02   :: [O] B01 = Biomass; B02 = Fossil Brown coal/Lignite; B03 = Fossil Coal-derived gas; B04 = Fossil Gas; B05 = Fossil Hard coal; B06 = Fossil Oil; B07 = Fossil Oil shale; B08 = Fossil Peat; B09 = Geothermal; B10 = Hydro Pumped Storage; B11 = Hydro Run-of-river and poundage; B12 = Hydro Water Reservoir; B13 = Marine; B14 = Nuclear; B15 = Other renewable; B16 = Solar; B17 = Waste; B18 = Wind Offshore; B19 = Wind Onshore; B20 = Other; B25 = Energy storage

### [Transmission] 12.1.G Cross-Border Physical Flows
METHOD: GET
URL: {{baseUrl}}?documentType=A11&out_Domain=10YDE-RWENET---I&in_Domain=10YBE----------2&periodStart=202308232200&periodEnd=202308242200
DESC: Request limit: Each request may cover a period of up to 1 year. Unlike Web GUI, API responds not netted values as data is requested per direction.
    - documentType = A11   :: [M] A11 = Aggregated energy data report
    - out_Domain = 10YDE-RWENET---I   :: [M] EIC code of a Control Area, Bidding Zone, Country
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area, Bidding Zone, Country
    - periodStart = 202308232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 11.1.A Forecasted Transfer Capacities
METHOD: GET
URL: {{baseUrl}}?documentType=A61&contract_MarketAgreement.Type=A01&out_Domain=10YGB----------A&in_Domain=10YBE----------2&periodStart=202308152200&periodEnd=202308162200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A61   :: [M] A61 = Estimated Net Transfer Capacity
    - contract_MarketAgreement.Type = A01   :: [M] A01 = Day ahead; A02 = Week ahead; A03 = Month ahead; A04 = Year ahead
    - out_Domain = 10YGB----------A   :: [M] EIC code of a Control Area or Bidding Zone
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area or Bidding Zone
    - periodStart = 202308152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 12.1.F Commercial Schedules
METHOD: GET
URL: {{baseUrl}}?documentType=A09&out_Domain=10Y1001A1001A82H&in_Domain=10YFR-RTE------C&periodStart=202308232200&periodEnd=202308242200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A09   :: [M] A09 = Finalised schedule
    - out_Domain = 10Y1001A1001A82H   :: [M] EIC code of a Control Area, Bidding Zone or a Country
    - in_Domain = 10YFR-RTE------C   :: [M] EIC code of a Control Area, Bidding Zone or a Country
    - periodStart = 202308232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - contract_MarketAgreement.Type = A01   :: [O] A01 = Day Ahead Commercial Schedules; A05 = Total Commercial Schedules
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 12.1.F Commercial Schedules - Net Positions
METHOD: GET
URL: {{baseUrl}}?documentType=A09&businessType=B09&out_Domain=10YAT-APG------L&in_Domain=10YAT-APG------L&periodStart=202506102200&periodEnd=202506112200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A09   :: [M] A09 = Finalised schedule
    - businessType = B09   :: [M] B09 = Net position
    - out_Domain = 10YAT-APG------L   :: [M] EIC code of a Control Area, Bidding Zone or a Country
    - in_Domain = 10YAT-APG------L   :: [M] EIC code of a Control Area, Bidding Zone or a Country (same as above)
    - periodStart = 202506102200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202506112200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - contract_MarketAgreement.Type = A01   :: [O] A01 = Day Ahead Commercial Schedules; A05 = Total Commercial Schedules
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 11.3 Cross Border Capacity of DC Links - Intraday Transfer Limits
METHOD: GET
URL: {{baseUrl}}?documentType=A93&out_Domain=11Y0-0000-0265-K&in_Domain=10YFR-RTE------C&periodStart=202308160000&periodEnd=202308162200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A93   :: [M] A93 = DC link capacity
    - out_Domain = 11Y0-0000-0265-K   :: [M] EIC code of a Bidding Zone, Control Area or Country
    - in_Domain = 10YFR-RTE------C   :: [M] EIC code of a Bidding Zone, Control Area or Country
    - periodStart = 202308160000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202308162200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 13.1.C Costs of Congestion Management
METHOD: GET
URL: {{baseUrl}}?documentType=A92&out_Domain=10YBE----------2&in_Domain=10YBE----------2&periodStart=202112312300&periodEnd=202212312300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A92   :: [M] A92 = Congestion costs
    - out_Domain = 10YBE----------2   :: [M] EIC code of a Control Area
    - in_Domain = 10YBE----------2   :: [M] EIC code of a Control Area (same as out_Domain)
    - periodStart = 202112312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202212312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 13.1.A Redispatching Internal
METHOD: GET
URL: {{baseUrl}}?documentType=A63&businessType=A85&out_Domain=10YNL----------L&in_Domain=10YNL----------L&periodStart=202310312300&periodEnd=202311302300
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A63   :: [M] A63 = Redispatch notice
    - businessType = A85   :: [M] A85 = Internal requirements
    - out_Domain = 10YNL----------L   :: [M] EIC code of a Control Area
    - in_Domain = 10YNL----------L   :: [M] EIC code of a Control Area (must be same as out_Domain)
    - periodStart = 202310312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202311302300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 13.1.A Redispatching Cross Border
METHOD: GET
URL: {{baseUrl}}?documentType=A63&businessType=A46&out_Domain=10YAT-APG------L&in_Domain=10YFR-RTE------C&periodStart=202311010000&periodEnd=202312010000
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A63   :: [M] A63 = Redispatch notice
    - businessType = A46   :: [M] A46 = System Operator re-dispatching
    - out_Domain = 10YAT-APG------L   :: [M] EIC code of a Control Area
    - in_Domain = 10YFR-RTE------C   :: [M] EIC code of a Control Area
    - periodStart = 202311010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 9.1 Expansion and Dismantling Project
METHOD: GET
URL: {{baseUrl}}?documentType=A90&out_Domain=10YHU-MAVIR----U&in_Domain=10YSK-SEPS-----K&periodStart=202301010000&periodEnd=202312312300
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A90   :: [M] A90 = Interconnector network expension
    - out_Domain = 10YHU-MAVIR----U   :: [M] EIC code of a Bidding Zone or a Control Area
    - in_Domain = 10YSK-SEPS-----K   :: [M] EIC code of a Bidding Zone or a Control Area
    - periodStart = 202301010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - businessType = B01   :: [O] B01 = interconnector network evolution; B02 = interconnector network dismantling
    - DocStatus = A01   :: [O] A01 = Intermediate; A02 = Final; A05 = Active; A09 = Cancelled; A13 = Withdrawn; X01 = Estimated
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Transmission] 13.1.B Countertrading
METHOD: GET
URL: {{baseUrl}}?documentType=A91&out_Domain=10YES-REE------0&in_Domain=10YFR-RTE------C&periodStart=202309122200&periodEnd=202309132200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A91   :: [M] A91 = Counter trade notice
    - out_Domain = 10YES-REE------0   :: [M] EIC code of a Control Area, or Bidding Zone
    - in_Domain = 10YFR-RTE------C   :: [M] EIC code of a Control Area, or Bidding Zone
    - periodStart = 202309122200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202309132200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Outages] 15.1.C-D Unavailability of Production Units
METHOD: GET
URL: {{baseUrl}}?documentType=A77&BiddingZone_Domain=10YBE----------2&periodStart=202212312300&periodEnd=202301312300
DESC: Request limit: Each request may cover a period of up to 1 year. It applies to PeriodStart and PeriodEnd if PeriodStartUpdate and PeriodEndUpdate parameters are not included in the request. It applies only to PeriodStartUpdate and PeriodEndUpdate if included in the request. Response limit : A maximum of 200 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 200 XML documents, where offset=0 returns the first 200 documents, offset=200 returns the next 200, and so on.
    - documentType = A77   :: [M] A77 = Production unit unavailability
    - BiddingZone_Domain = 10YBE----------2   :: [M] EIC code of a Control Area, Bidding Zone (optional if mRID is present)
    - periodStart = 202212312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202301312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - BusinessType = A53   :: [O] A53 = Planned maintenance; A54 = Forced unavailability (unplanned outage)
    - DocStatus = A05   :: [O] A05 = Active; A09 = Cancelled; A13 = Withdrawn; (when not defined only Active and Cancelled outages are returned)
    - PeriodStartUpdate = 202301152300   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - PeriodEndUpdate = 202301312300   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - RegisteredResource = 22W20200608A---8   :: [O] EIC Code of Production Unit
    - mRID = -WmcUg9Da9u8AF3A_gx8UQ   :: [O] Older versions of an outage is returned only when mRID parameter is used
    - offset = 1   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 200 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+200).

### [Outages] 15.1.A&B Unavailability of Generation Units
METHOD: GET
URL: {{baseUrl}}?documentType=A80&BiddingZone_Domain=10YBE----------2&periodStart=202301022200&periodEnd=202401022200
DESC: Request limit: Each request may cover a period of up to 1 year. It applies to PeriodStart and PeriodEnd if PeriodStartUpdate and PeriodEndUpdate parameters are not included in the request. It applies only to PeriodStartUpdate and PeriodEndUpdate if included in the request. Response limit : A maximum of 200 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 200 XML documents, where offset=0 returns the first 200 documents, offset=200 returns the next 200, and so on.
    - documentType = A80   :: [M] A80 = Generation unavailability
    - BiddingZone_Domain = 10YBE----------2   :: [M] Control Area, Bidding Zone (optional if mRID is present)
    - periodStart = 202301022200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202401022200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - BusinessType = A53   :: [O] A53 = Planned maintenance; A54 = Forced unavailability (unplanned outage)
    - DocStatus = A05   :: [O] DocStatus (when not defined only Active and Cancelled outages are returned): A05 = Active; A09 = Cancelled; A13 = Withdrawn
    - PeriodStartUpdate = 202301031000   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - PeriodEndUpdate = 202301032200   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - RegisteredResource = 22WCOOX6X000064W   :: [O] EIC Code of Generation Unit
    - mRID = nCYGn4HPvOBiVrWtRFL35g   :: [O] Used to retrieve older versions of an outage
    - offset = 0   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 200 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+200).

### [Outages] 7.1.A-B Aggregated Unavailability of Consumption Units
METHOD: GET
URL: {{baseUrl}}?documentType=A76&BiddingZone_Domain=10Y1001A1001A82H&periodStart=202310312300&periodEnd=202311302300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A76   :: [M] A76 = Load unavailability
    - BiddingZone_Domain = 10Y1001A1001A82H   :: [M] EIC code of a Control Area or a Bidding Zone (optional if mRID is present)
    - periodStart = 202310312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000 (optional if PeriodStartUpdate is defined)
    - periodEnd = 202311302300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000 (optional if PeriodEndUpdate is defined)
    - BusinessType = A53   :: [O] A53 = Planned maintenance; A54 = Forced unavailability (unplanned outage)
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Outages] 10.1.A&B Unavailability of Transmission Infrastructure
METHOD: GET
URL: {{baseUrl}}?documentType=A78&Out_Domain=10YFR-RTE------C&In_Domain=10YBE----------2&periodStart=202312012300&periodEnd=202312022300
DESC: Request limit: Each request may cover a period of up to 1 year. It applies to PeriodStart and PeriodEnd if PeriodStartUpdate and PeriodEndUpdate parameters are not included in the request. It applies only to PeriodStartUpdate and PeriodEndUpdate if included in the request. Response limit : A maximum of 200 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 200 XML documents, where offset=0 returns the first 200 documents, offset=200 returns the next 200, and so on.
    - documentType = A78   :: [M] A78 = Transmission unavailability
    - Out_Domain = 10YFR-RTE------C   :: [M] Control Area, Bidding Zone (optional if mRID is present)
    - In_Domain = 10YBE----------2   :: [M] Control Area, Bidding Zone (optional if mRID is present)
    - periodStart = 202312012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312022300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - BusinessType = A53   :: [O] A53 = Planned maintenance; A54 = Forced unavailability (unplanned outage)
    - DocStatus = A05   :: [O] DocStatus (when not defined only Active and Cancelled outages are returned) A05 = Active A09 = Cancelled A13 = Withdrawn
    - PeriodStartUpdate = 202111090000   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - PeriodEndUpdate = 202112212300   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - mRID = A47mJe5e9jml9FeSL6jfKg   :: [O] Used to retrieve previous outage versions
    - offset = 0   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 200 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+200).

### [Outages] 10.1.A&B Unavailability of Transmission Infrastructure - Available Capacity
METHOD: GET
URL: {{baseUrl}}?documentType=A78&ControlArea_Domain=10YFR-RTE------C&periodStart=202312012300&periodEnd=202312022300
DESC: Request limit: Each request may cover a period of up to 1 year. It applies to PeriodStart and PeriodEnd if PeriodStartUpdate and PeriodEndUpdate parameters are not included in the request. It applies only to PeriodStartUpdate and PeriodEndUpdate if included in the request. Response limit : A maximum of 200 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 200 XML documents, where offset=0 returns the first 200 documents, offset=200 returns the next 200, and so on.
    - documentType = A78   :: [M] A78 = Transmission unavailability
    - ControlArea_Domain = 10YFR-RTE------C   :: [M] Control Area, Bidding Zone (optional if mRID is present)
    - periodStart = 202312012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312022300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - BusinessType = A53   :: [O] A53 = Planned maintenance; A54 = Forced unavailability (unplanned outage)
    - Asset_RegisteredResource.mRID =    :: [O] EIC code of a Transmission Asset
    - DocStatus = A05   :: [O] DocStatus (when not defined only Active and Cancelled outages are returned) A05 = Active A09 = Cancelled A13 = Withdrawn
    - PeriodStartUpdate = 202111090000   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - PeriodEndUpdate = 202112212300   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - mRID = A47mJe5e9jml9FeSL6jfKg   :: [O] Used to retrieve previous outage versions
    - offset = 0   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 200 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+200).

### [Outages] 10.1.A&B Unavailability of Transmission Infrastructure  - Net Position Impact
METHOD: GET
URL: {{baseUrl}}?documentType=A78&pTDF_Domain.mRID=10YBE----------2&periodStart=202312012300&periodEnd=202312022300
DESC: Request limit: Each request may cover a period of up to 1 year. It applies to PeriodStart and PeriodEnd if PeriodStartUpdate and PeriodEndUpdate parameters are not included in the request. It applies only to PeriodStartUpdate and PeriodEndUpdate if included in the request. Response limit : A maximum of 200 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 200 XML documents, where offset=0 returns the first 200 documents, offset=200 returns the next 200, and so on.
    - documentType = A78   :: [M] A78 = Transmission unavailability
    - pTDF_Domain.mRID = 10YBE----------2   :: [M] Control Area, Bidding Zone (optional if mRID is present)
    - periodStart = 202312012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312022300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - BusinessType = A53   :: [O] A53 = Planned maintenance; A54 = Forced unavailability (unplanned outage)
    - DocStatus = A05   :: [O] DocStatus (when not defined only Active and Cancelled outages are returned) A05 = Active A09 = Cancelled A13 = Withdrawn
    - PeriodStartUpdate = 202111090000   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - PeriodEndUpdate = 202112212300   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000
    - mRID = A47mJe5e9jml9FeSL6jfKg   :: [O] Used to retrieve previous outage versions
    - offset = 0   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 200 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+200).
    - Asset_RegisteredResource.mRID =    :: EIC Code of the Transmission Asset

### [Outages] 10.1.C Unavailability of Offshore Grid Infrastructure
METHOD: GET
URL: {{baseUrl}}?documentType=A79&BiddingZone_Domain=10Y1001A1001A82H&periodStart=202301142300&periodEnd=202301152300
DESC: Request limit: Each request may cover a period of up to 1 year. It applies to PeriodStart and PeriodEnd if PeriodStartUpdate and PeriodEndUpdate parameters are not included in the request. It applies only to PeriodStartUpdate and PeriodEndUpdate if included in the request. Response limit : A maximum of 200 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 200 XML documents, where offset=0 returns the first 200 documents, offset=200 returns the next 200, and so on.
    - documentType = A79   :: [M] A79 = Offshore grid infrastructure unavailability
    - BiddingZone_Domain = 10Y1001A1001A82H   :: [M] EIC code of a Control Area, Bidding Zone (optional if mRID is present)
    - periodStart = 202301142300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000 (optional if PeriodStartUpdate is defined)
    - periodEnd = 202301152300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000 (optional if PeriodEndUpdate is defined)
    - DocStatus = A05   :: [O] DocStatus (when not defined only Active and Cancelled outages are returned) - A05 = Active; A09 = Cancelled; A13 = Withdrawn
    - PeriodStartUpdate = 202312010000   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000 (mandatory if PeriodStart and PeriodEnd are not defined)
    - PeriodEndUpdate = 202312020000   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000 (mandatory if PeriodStart and PeriodEnd are not defined)
    - mRID =    :: [O] Used to retrieve previous outage versions
    - offset = 0   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 200 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+200).

### [Outages] Fall-backs [IFs IN 7.2, mFRR 3.11, aFRR 3.10]
METHOD: GET
URL: {{baseUrl}}?documentType=A53&ProcessType=A51&BusinessType=C47&BiddingZone_Domain=10YBE----------2&periodStart=202301010000&periodEnd=202401020000
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 100 XML documents, where offset=0 returns the first 100 documents, offset=100 returns the next 100, and so on.
    - documentType = A53   :: [M] A53 = Outage publication document
    - ProcessType = A51   :: [M] A47 = Manual frequency restoration reserve; A51 = Automatic frequency restoration reserve; A63 = Imbalance Netting
    - BusinessType = C47   :: [M] C47 = Disconnection; A53 = Planned maintenance; A54: Unplanned outage; A83 = Auction cancellation (used in case no solution found or algorithm failure)
    - BiddingZone_Domain = 10YBE----------2   :: [M] EIC code of a CTA/LFA/REG
    - periodStart = 202301010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000 (optional if PeriodStartUpdate is defined)
    - periodEnd = 202401020000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000 (optional if PeriodEndUpdate is defined)
    - DocStatus = A13   :: [O] A13: Withdrawn (used to return withdrawn documents). By default withdrawn publications are not returned.
    - mRID =    :: [O] Used to retrieve previous publication versions
    - offset = 0   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 100 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+100).

### [Balancing] 17.1.F Prices of Activated Balancing Energy
METHOD: GET
URL: {{baseUrl}}?documentType=A84&processType=A16&controlArea_Domain=10YBE----------2&periodStart=202309032200&periodEnd=202309042200&businessType=A96
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A84   :: [M] A84 = Activated balancing prices
    - processType = A16   :: [M] A16 = Realised; A60 = Scheduled activation mFRR; A61 = Direct activation mFRR; A68 = Local Selection aFRR
    - controlArea_Domain = 10YBE----------2   :: [M] EIC Code of a LFA, IPA, or a SCA
    - periodStart = 202309032200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202309042200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - businessType = A96   :: [O] A95 = Frequency containment reserve; A96 = Automatic frequency restoration reserve; A97 = Manual frequency restoration reserve; A98 = Replacement reserve
    - ExportType = zip   :: [O] Note: This parameter is planned to be discontinued in R3.09 (October 2023)
    - PsrType = A04   :: [O] A04 = Generation; A05 = Load
    - Standard_MarketProduct = A01   :: [O] A01 = Standard
    - Original_MarketProduct = A02   :: [O] A02 = Specific; A04 = Local
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] IF aFRR 3.16 Cross Border Marginal Prices (CBMPs) for aFRR Central Selection (CS)
METHOD: GET
URL: {{baseUrl}}?documentType=A84&processType=A67&businessType=A96&Standard_MarketProduct=A01&controlArea_Domain=10YDE-VE-------2&periodStart=202311082300&periodEnd=202311092300
DESC: Request limit: Each request may cover a period of up to 1 day.
    - documentType = A84   :: [M] A84 = Activated balancing prices
    - processType = A67   :: [M] A67 = Central Selection aFRR
    - businessType = A96   :: [M] A96 = automatic frequency restoration reserve
    - Standard_MarketProduct = A01   :: [M] A01 = Standard
    - controlArea_Domain = 10YDE-VE-------2   :: [M] EIC code of a LFA, SCA, IPA
    - periodStart = 202311082300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202311092300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000

### [Balancing] 12.3.B&C Balancing energy bids
METHOD: GET
URL: {{baseUrl}}?documentType=A37&businessType=B74&processType=A47&connecting_Domain=10YBE----------2&periodStart=202310072200&periodEnd=202310082200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements in total, counted across all XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A37   :: [M] A37 = Reserve bid document
    - businessType = B74   :: [M] B74 = Offer
    - processType = A47   :: [M] A46 = Replacement reserve; A47 = Manual frequency restoration reserve; A51 = Automatic frequency restoration reserve
    - connecting_Domain = 10YBE----------2   :: [M] EIC code of a Scheduling Area
    - periodStart = 202310072200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000. Note data is archived after 93 days of retention period. Therefore the requested date should be within the retention period.
    - periodEnd = 202310082200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000. Note data is archived after 93 days of retention period. Therefore the requested date should be within the retention period.
    - offset = 1000   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).
    - Standard_MarketProduct = A01   :: [O] A01 = Standard; A05 = Standard mFRR scheduled activation; A07 = Standard mFRR direct activation
    - Original_MarketProduct = A02   :: [O] A02 = Specific; A03 = Integrated Process; A04 = Local
    - Direction = A01   :: [O] A01 = Up; A02 = Down

### [Balancing] 12.3.B&C Balancing energy bids archives
METHOD: GET
URL: {{baseUrl}}?documentType=A37&businessType=B74&processType=A47&connecting_Domain=10YBE----------2&periodStart=202310072200&periodEnd=202310082200&storageType=archive &offset=0
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 ZIP files contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 100 ZIP archives, where offset=0 returns the first 100 archives, offset=100 returns the next 100, and so on.
    - documentType = A37   :: [M] A37 = Reserve bid document
    - businessType = B74   :: [M] B74 = Offer
    - processType = A47   :: [M] A46 = Replacement reserve; A47 = Manual frequency restoration reserve; A51 = Automatic frequency restoration reserve.
    - connecting_Domain = 10YBE----------2   :: [M] EIC code of a Scheduling Area
    - periodStart = 202310072200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000. Note data is archived after 93 days of retention period. Therefore the requested period should not be within the retention period.
    - periodEnd = 202310082200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000. Note data is archived after 93 days of retention period. Therefore the requested period should not be within the retention period.
    - storageType = archive    :: [M] Used to request archives
    - offset = 0   :: [O] Integer: Zero‑based index of the first archive to return. The offset parameter paginates the response in batches of 100 archives (e.g., offset = n returns the archives in the range n+1 to n+100).

### [Balancing] IFs mFRR 9.9, aFRR 9.6&9.8 Changes to Bid Availability
METHOD: GET
URL: {{baseUrl}}?documentType=B45&processType=A47&Domain=10YDE-VE-------2&periodStart=202309232200&periodEnd=202309242200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = B45   :: [M] B45 = Bid Availability Document
    - processType = A47   :: [M] A47: mFRR; A51: aFRR
    - Domain = 10YDE-VE-------2   :: [M] EIC code of a Scheduling Area or LFA
    - periodStart = 202309232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202309242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - businessType = C46   :: [O] C40 = Conditional bid; C41 = Thermal limit; C42 = Frequency limit; C43 = Voltage limit; C44 = Current limit; C45 = Short-circuit current limits; C46 = Dynamic stability limit
    - offset = 100   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).

### [Balancing] IFs mFRR 9.9, aFRR 9.6&9.8 Changes to Bid Availability Archives
METHOD: GET
URL: {{baseUrl}}?documentType=B45&processType=A47&Domain=10YDE-VE-------2&periodStart=202309232200&periodEnd=202309242200&storageType=archive
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 ZIP files contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 100 ZIP archives, where offset=0 returns the first 100 archives, offset=100 returns the next 100, and so on.
    - documentType = B45   :: [M] B45 = Bid Availability Document
    - processType = A47   :: [M] A47: mFRR; A51: aFRR
    - Domain = 10YDE-VE-------2   :: [M] EIC code of a Scheduling Area or LFA
    - periodStart = 202309232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202309242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - storageType = archive   :: [M] Used to request archives
    - businessType = C46   :: [O] C40 = Conditional bid; C41 = Thermal limit; C42 = Frequency limit; C43 = Voltage limit; C44 = Current limit; C45 = Short-circuit current limits; C46 = Dynamic stability limit
    - offset = 100   :: [O] Integer: Zero‑based index of the first archive to return. The offset parameter paginates the response in batches of 100 archives (e.g., offset = n returns the archives in the range n+1 to n+100).

### [Balancing] 12.3.E Aggregated Balancing Energy Bids (GL EB)
METHOD: GET
URL: {{baseUrl}}?documentType=A24&processType=A51&area_Domain=10YAT-APG------L&periodStart=202309022200&periodEnd=202309032200&curveType=A03
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A24   :: [M] A24 = Bid document
    - processType = A51   :: [M] A51 = Automatic frequency restoration reserve; A46 = Replacement reserve; A47 = Manual frequency restoration reserve; A60 = Scheduled activation mFRR; A61 = Direct activation mFRR; A67 = Central Selection aFRR; A68 = Local Selection aFRR
    - area_Domain = 10YAT-APG------L   :: [M] EIC code of a Scheduling Area
    - periodStart = 202309022200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202309032200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] IFs 3.10, 3.16 & 3.17 Netted and Exchanged Volumes
METHOD: GET
URL: {{baseUrl}}?documentType=B17&processType=A63&Acquiring_Domain=10YDE-VE-------2&Connecting_Domain=10YDE-VE-------2&periodStart=202301012300&periodEnd=202301022300
DESC: Request limit: For aFRR: Each request may cover a period of up to 1 day. For other process types: Each request may cover a period of up to 1 year.
    - documentType = B17   :: [M] B17 = Aggregated netted external TSO schedule document
    - processType = A63   :: [M] A60 = mFRR with Scheduled Activation; A61 = mFRR with Direct Activation; A51 = Automatic Frequency Restoration Reserve; A63= Imbalance Netting
    - Acquiring_Domain = 10YDE-VE-------2   :: [M] EIC code of a LFA or SCA
    - Connecting_Domain = 10YDE-VE-------2   :: [M] EIC code of a LFA or SCA
    - periodStart = 202301012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202301022300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000

### [Balancing] IFs 3.10, 3.16 & 3.17 Netted and Exchanged Volumes per Border
METHOD: GET
URL: {{baseUrl}}?documentType=A30&processType=A60&Acquiring_Domain=10YBE----------2&Connecting_Domain=10YFR-RTE------C&periodStart=202503010000&periodEnd=202503020000
DESC: Request limit: For aFRR: Each request may cover a period of up to 1 day. For other process types: Each request may cover a period of up to 1 year.
    - documentType = A30   :: [M] A30 = Cross border schedule
    - processType = A60   :: [M] A60 = mFRR with Scheduled Activation; A61 = mFRR with Direct Activation; A51 = Automatic Frequency Restoration Reserve; A63= Imbalance Netting
    - Acquiring_Domain = 10YBE----------2   :: [M] EIC code of a LFA or SCA
    - Connecting_Domain = 10YFR-RTE------C   :: [M] EIC code of a LFA or SCA
    - periodStart = 202503010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202503020000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000

### [Balancing] IFs aFRR 3.4 & mFRR 3.4 Elastic Demands
METHOD: GET
URL: {{baseUrl}}?documentType=A37&businessType=B75&processType=A47&Acquiring_Domain=10YCZ-CEPS-----N&periodStart=202311302300&periodEnd=202312012300
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A37   :: [M] A37 = Reserve bid document
    - businessType = B75   :: [M] B75 = Need
    - processType = A47   :: [M] A51 = Automatic Frequency Restoration Reserve; A47 = Manual Frequency Restoration Reserve
    - Acquiring_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Scheduling Area
    - periodStart = 202311302300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202312012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - offset = 0   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).

### [Balancing] 17.1.B&C Volumes and Prices of Contracted Reserves
METHOD: GET
URL: {{baseUrl}}?documentType=A81&businessType=B95&Type_MarketAgreement.Type=A01&controlArea_Domain=10YCZ-CEPS-----N&periodStart=202309242200&periodEnd=202309252200&processType=A52
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements in total, counted across all XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A81   :: [M] A81 = Contracted reserves
    - businessType = B95   :: [M] B95 = Procured capacity
    - Type_MarketAgreement.Type = A01   :: [M] A01 = Daily; A02 = Weekly; A03 = Monthly; A04 = Yearly; A06 = Long term; A13 = Hourly
    - controlArea_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of a Scheduling Area
    - periodStart = 202309242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202309252200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - processType = A52   :: [O] A51 = Automatic frequency restoration reserve; A52 = Frequency containment reserve; A47 = Manual frequency restoration reserve; A46 = Replacement reserve
    - psrType = A04   :: [O] A03 = Mixed; A04 = Generation; A05 = Load
    - offset = 0   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).

### [Balancing] 12.3.F Procured balancing capacity (GL EB)
METHOD: GET
URL: {{baseUrl}}?documentType=A15&processType=A51&area_Domain=10YDE-VE-------2&periodStart=202306150000&periodEnd=202306150100&offset=0&Type_MarketAgreement.Type=A01
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements in total, counted across all XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A15   :: [M] A15 = Acquiring system operator reserve schedule
    - processType = A51   :: [M] A46 = Replacement reserve; A47 = Manual frequency restoration reserve; A51 = Automatic frequency restoration reserve; A52 = Frequency containment reserve
    - area_Domain = 10YDE-VE-------2   :: [M] Scheduling Area
    - periodStart = 202306150000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202306150100   :: [M ]Pattern yyyyMMddHHmm e.g. 201601010000 (IMPOTANT NOTE: Minimum time interval in query response ranges from part of day to year, depending on selected Type_MarketAgreement.Type. Minimum is 1 hour for this data item.)
    - offset = 0   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).
    - Type_MarketAgreement.Type = A01   :: [O] A01 = Daily; A02 = Weekly; A03 = Monthly; A04 = Yearly; A05 = Total; A06 = Long term; A07 = Intraday; A13 = Hourly

### [Balancing] 187.2 FCR Total capacity (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&businessType=A25&area_Domain=10YEU-CONT-SYNC0&periodStart=202312312300&periodEnd=202412312300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A26   :: A26 = Capacity document
    - businessType = A25   :: A25 = General Capacity Information
    - area_Domain = 10YEU-CONT-SYNC0   :: Synchronous Area
    - periodStart = 202312312300   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202412312300   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 187.2 Shares of FCR capacity (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&businessType=C23&area_Domain=10YFR-RTE------C&periodStart=202312312300&periodEnd=202412312300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A26   :: A26 = Capacity document
    - businessType = C23   :: C23 = Share of reserve capacity
    - area_Domain = 10YFR-RTE------C   :: Synchronous Area
    - periodStart = 202312312300   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202412312300   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 190.2 Sharing of FCR between SAs (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&processType=A52&businessType=C22&area_Domain=10Y1001A1001A59C&periodStart=201510302300&periodEnd=201512152300
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A26   :: A26 = Capacity document
    - processType = A52   :: A52 = Frequency containment reserve
    - businessType = C22   :: C22 = Shared Balancing Reserve Capacity
    - area_Domain = 10Y1001A1001A59C   :: Scheduling Area
    - periodStart = 201510302300   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 201512152300   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - offset = 0   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 188.3 & 189.2 FRR & RR Capacity Outlook (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&processType=A56&businessType=C76&area_Domain=10YAT-APG------L&periodStart=202312312300&periodEnd=202412312300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A26   :: [M] A26 = Capacity document
    - processType = A56   :: [M] A46 = Replacement Reserve; A56 = Frequency Restoration Reserve
    - businessType = C76   :: [M] C76 = Forecasted capacity
    - area_Domain = 10YAT-APG------L   :: [M] EIC code of LFB Area
    - periodStart = 202312312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202412312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000

### [Balancing] 188.4 & 189.3 FRR and RR Actual Capacity (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&processType=A56&businessType=C77&area_Domain=10YAT-APG------L&periodStart=202312312300&periodEnd=202403312200
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A26   :: [M] A26 = Capacity document
    - processType = A56   :: [M] A46 = Replacement reserve; A56 = Frequency restoration reserve
    - businessType = C77   :: [M] C77 = Min; C78 = Avg; C79 = Max
    - area_Domain = 10YAT-APG------L   :: [M] EIC Code of LFB Area
    - periodStart = 202312312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202403312200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 189.2 Outlook of Reserve Capacities on RR (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&processType=A46&businessType=C76&area_Domain=10YCZ-CEPS-----N&periodStart=202212310000&periodEnd=202305010000&offset=100
DESC: 
    - documentType = A26   :: A26 = Capacity document
    - processType = A46   :: A46 = Replacement reserve
    - businessType = C76   :: C76 = Forecasted capacity
    - area_Domain = 10YCZ-CEPS-----N   :: Scheduling Area
    - periodStart = 202212310000   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202305010000   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - offset = 100   :: Optional parameter

### [Balancing] 189.3 RR Actual Capacity(SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&processType=A46&businessType=C77&area_Domain=10YCZ-CEPS-----N&periodStart=202212310000&periodEnd=202305010000&offset=100
DESC: 
    - documentType = A26   :: A26 = Capacity document
    - processType = A46   :: A46 = Replacement reserve
    - businessType = C77   :: C77 = Min
    - area_Domain = 10YCZ-CEPS-----N   :: Scheduling Area
    - periodStart = 202212310000   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202305010000   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - offset = 100   :: Optional parameter

### [Balancing] 17.1.I Financial Expenses and Income for Balancing
METHOD: GET
URL: {{baseUrl}}?documentType=A87&controlArea_Domain=10YHU-MAVIR----U&periodStart=202301312300&periodEnd=202302282300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A87   :: [M] A87 = Financial situation
    - controlArea_Domain = 10YHU-MAVIR----U   :: [M] EIC code of a Control Area or a Market Balance Area
    - periodStart = 202301312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202302282300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 12.3.H&I Allocation and use of cross-zonal balancing capacity
METHOD: GET
URL: {{baseUrl}}?documentType=A38&processType=A51&Connecting_Domain=10Y1001A1001A47J&Acquiring_Domain=10YDK-2--------M&periodStart=202306150000&periodEnd=202306152200
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 instances contained in the ZIP response. One instance can be split into up to 8 TimeSeries. The total number of files in the ZIP file is variable and depends on the values of the dividing elements - allocation decision time, domain.mRID, etc.
    - documentType = A38   :: [M] A38 = Reserve allocation result document
    - processType = A51   :: [M] A46 = Replacement reserve; A47 = Manual frequency restoration reserve; A51 = Automatic frequency restoration reserve; A52 = Frequency containment reserve
    - Connecting_Domain = 10Y1001A1001A47J   :: [M] EIC code of a Bidding Zone
    - Acquiring_Domain = 10YDK-2--------M   :: [M] EIC code of a Bidding Zone
    - periodStart = 202306150000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202306152200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - Type_MarketAgreement.Type = A01   :: [O] A01 = Daily; A02 = Weekly; A06 = Long term
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] IFs 4.5 Permanent Allocation Limitations to Cross-border Capacity on HVDC Lines
METHOD: GET
URL: {{baseUrl}}?documentType=A99&processType=A63&BusinessType=B06&Out_Domain=10YNL----------L&In_Domain=10YDK-1--------W&periodStart=202101010000&periodEnd=202112310000&registeredResource=10T-DK-NL-000012
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response.
    - documentType = A99   :: [M] A99 = HVDC Link constraints
    - processType = A63   :: [M] A51 = Automatic Frequency Restoration Reserve; A63= Imbalance Netting; A47 = Manual frequency restoration reserve
    - BusinessType = B06   :: [M] B06 = DC Link constraint
    - Out_Domain = 10YNL----------L   :: [M] EIC code of a Scheduling Area or LFC area
    - In_Domain = 10YDK-1--------W   :: [M] EIC code of a Scheduling Area or LFC area
    - periodStart = 202101010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202112310000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - registeredResource = 10T-DK-NL-000012   :: [O] EIC of interconnector (If used, data for the given Transmission Asset is returned, otherwise, data for IC not specified is returned.)
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] IFs 4.3 & 4.4 Balancing Border Capacity Limitations
METHOD: GET
URL: {{baseUrl}}?documentType=A31&BusinessType=A26&processType=A47&Out_Domain=10YCZ-CEPS-----N&In_Domain=10YAT-APG------L&periodStart=202401312300&periodEnd=202402012300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A31   :: [M] A31 = Agreed capacity
    - BusinessType = A26   :: [M] A26 = Available Transfer Capacity
    - processType = A47   :: [M] A51 = Automatic Frequency Restoration Reserve; A63= Imbalance Netting; A47 = Manual frequency restoration reserve
    - Out_Domain = 10YCZ-CEPS-----N   :: [M] EIC code of an LFC Area (LFA) or Scheduling area (SCA)
    - In_Domain = 10YAT-APG------L   :: [M] EIC code of an LFC Area (LFA) or Scheduling area (SCA)
    - periodStart = 202401312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202402012300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - registeredResource = 22T201903146---W   :: [O] EIC code of a Transmission Asset: If used, data for the given Transmission Asset is returned, otherwise, data for IC not specified is returned.
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 190.1 Sharing of RR and FRR (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&BusinessType=C22&processType=A51&Area_Domain=10YAT-APG------L&periodStart=202101010000&periodEnd=202112310000&curveType=A01
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements is returned per XML response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A26   :: [M] A26 = Capacity document
    - BusinessType = C22   :: [M] C22 = Shared balancing reserve capacity
    - processType = A51   :: [M] A51 = Automatic Frequency Restoration Reserve; A47 = Manual Frequency Restoration Reserve; A46 = Replacement Reserve
    - Area_Domain = 10YAT-APG------L   :: [M] Load Frequency Control Block
    - periodStart = 202101010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202112310000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A01   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 190.3 Exchanged Reserve Capacity (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A26&processType=A46&BusinessType=C21&Acquiring_Domain=10YAT-APG------L&Connecting_Domain=10YCB-GERMANY--8&periodStart=202101010000&periodEnd=202112310000
DESC: Request limit: Each request may cover a period of up to 1 year. Response limit : A maximum of 100 TimeSeries elements in total, counted across all XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 100 TimeSeries, where offset=0 returns the first 100 elements, offset=100 returns the next 100, and so on.
    - documentType = A26   :: A26 = Capacity document
    - processType = A46   :: A46 = Replacement reserve
    - BusinessType = C21   :: C21 = Exchanged balancing reserve capacity
    - Acquiring_Domain = 10YAT-APG------L   :: Load Frequency Control Block
    - Connecting_Domain = 10YCB-GERMANY--8   :: Load Frequency Control Block
    - periodStart = 202101010000   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202112310000   :: Pattern yyyyMMddHHmm e.g. 201601010000
    - Offset = 1   :: [O] Integer: Zero‑based index of the first TimeSeries to return. The offset parameter paginates the response in batches of 100 TimeSeries (e.g., offset = n returns the TimeSeries in the range n+1 to n+100).

### [Balancing] 17.1.G Imbalance prices
METHOD: GET
URL: {{baseUrl}}?documentType=A85&controlArea_Domain=10YAT-APG------L&periodStart=202401010000&periodEnd=202401050000
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A85   :: [M] A85 = Imbalance prices
    - controlArea_Domain = 10YAT-APG------L   :: [M] EIC code of a Scheduling Area or Market Balancing Area
    - periodStart = 202401010000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202401050000   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - PsrType = A04   :: [O] A04 = Generation; A05 = Load
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 17.1.H Total Imbalance Volumes
METHOD: GET
URL: {{baseUrl}}?documentType=A86&controlArea_Domain=10YAT-APG------L&periodStart=202311032300&periodEnd=202311042300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A86   :: [M] A86 = Imbalance volume
    - controlArea_Domain = 10YAT-APG------L   :: [M] EIC code of a Scheduling Area or Market Balance Area
    - periodStart = 202311032300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202311042300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - businessType = A19   :: [O] A19: Balance Energy Deviation (default value when not specified)
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 12.3.A Current balancing state [GL EB]
METHOD: GET
URL: {{baseUrl}}?documentType=A86&businessType=B33&area_Domain=10YHU-MAVIR----U&periodStart=202405292200&periodEnd=202405302200&curveType=A03
DESC: Request limit: Each request may cover a period of up to 100 days.
    - documentType = A86   :: [M] A86 = Imbalance volume
    - businessType = B33   :: [M] B33 = Area Control Error
    - area_Domain = 10YHU-MAVIR----U   :: [M] EIC code of a Scheduling Area
    - periodStart = 202405292200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202405302200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Balancing] 185.4 Results of the Criteria Application Process - Measurements (SO GL)
METHOD: GET
URL: {{baseUrl}}?documentType=A45&processType=A65&area_domain=10YCZ-CEPS-----N&periodStart=202209302200&periodEnd=202212312300
DESC: Request limit: Each request may cover a period of up to 1 year.
    - documentType = A45   :: [M] A45 = Measurement Value Document
    - processType = A65   :: [M] A64 = Criteria application for instantaneous frequency (For SNA); A65: Criteria application for frequency restoration (for LFC Block)
    - area_domain = 10YCZ-CEPS-----N   :: [M] EIC Code of a SNA (for processType A64) or LFC Block (for processType A65)
    - periodStart = 202209302200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202212312300   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - curveType = A03   :: [O] A01 = Sequential fixed block; A03 = Variable sized blocks (default)

### [Master Data] Production and Generation Units
METHOD: GET
URL: {{baseUrl}}?documentType=A95&businessType=B11&BiddingZone_Domain=10YBE----------2&Implementation_DateAndOrTime=2017-01-01
DESC: A production unit and its related generation units can be updated throughout their lifecycle. For example, installed capacity may change, production type may be modified, or a unit may be decommissioned for a certain period. Each change is recorded in the system as a new entry. Although this is not recommended, some data providers may create new records even when there is no actual change in master data. As a result, the same production unit (PU) and generation unit (GU) can appear multiple times under different timeseries elements in the API response. Each timeseries entry should be treated as a separate record. The implementation_DateAndOrTime.date field represents the start of validity for that record or definition. It remains valid until the next timeseries entry is created for the same PU. Unfortunately, timeseries elements do not include an explicit end validity date. When making a request, the implementation_DateAndOrTime value should be set to indicate the starting point from which you want to retrieve the relevant records.
    - documentType = A95   :: [M] A95 = Configuration document
    - businessType = B11   :: [M] B11 = Production unit
    - BiddingZone_Domain = 10YBE----------2   :: [M] EIC code of a Bidding Zone or a Control Area
    - Implementation_DateAndOrTime = 2017-01-01   :: [M] Pattern yyyy-MM-dd e.g. 2017-01-01
    - psrType = B04   :: [O] B01 = Biomass; B02 = Fossil Brown coal/Lignite; B03 = Fossil Coal-derived gas; B04 = Fossil Gas; B05 = Fossil Hard coal; B06 = Fossil Oil; B07 = Fossil Oil shale; B08 = Fossil Peat; B09 = Geothermal; B10 = Hydro Pumped Storage; B11 = Hydro Run-of-river and poundage; B12 = Hydro Water Reservoir; B13 = Marine; B14 = Nuclear; B15 = Other renewable; B16 = Solar; B17 = Waste; B18 = Wind Offshore; B19 = Wind Onshore; B20 = Other

### [OMI] Other Market Information
METHOD: GET
URL: {{baseUrl}}?documentType=B47&ControlArea_Domain=10YDE-EON------1&periodStart=202409232200&periodEnd=202409242200
DESC: Request limit: Each request may cover a period of up to 1 year. It applies to PeriodStart and PeriodEnd if PeriodStartUpdate and PeriodEndUpdate parameters are not included in the request. It applies only to PeriodStartUpdate and PeriodEndUpdate if included in the request. Response limit : A maximum of 200 XML documents contained in the ZIP response. The offset parameter can be used to retrieve the data in batches of up to 200 XML documents, where offset=0 returns the first 200 documents, offset=200 returns the next 200, and so on.
    - documentType = B47   :: [M] Other market information
    - ControlArea_Domain = 10YDE-EON------1   :: [M] EIC code of a Scheduling Area
    - periodStart = 202409232200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - periodEnd = 202409242200   :: [M] Pattern yyyyMMddHHmm e.g. 201601010000
    - DocStatus = A05   :: [O] A05: Active; A09: Cancelled; A13: Withdrawn
    - PeriodStartUpdate = 202402221000   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000 (mandatory if PeriodStart and PeriodEnd are not defined)
    - PeriodEndUpdate = 202402231200   :: [O] Pattern yyyyMMddHHmm e.g. 201601010000 (mandatory if PeriodStart and PeriodEnd are not defined)
    - Offset = 12   :: [O] Integer: Zero‑based index of the first XML document to return. The offset parameter paginates the response in batches of 200 XML documents (e.g., offset = n returns the XMLs in the range n+1 to n+200).
    - mRID = NDE5ODBiYjFkM2ExMTljYTM5Mzk2ODcxNDFkZDE4MzU=   :: [O] If mRID is included, individual versions of the particular event are queried using the rest of the parameters
