// Illustrative snapshots for the public product tour; no visitor data or API calls.
export const previewSamples = [
  {
    name: 'Customer churn', shortName: 'Churn', filename: 'customer_churn.csv',
    rows: '7,043', quality: '91', missing: '8.4%', ideas: '18',
    priorities: ['Review missing ages before modeling.', 'Standardize contract labels.', 'Exclude customer identifiers from predictive features.'],
    columns: [
      { name: 'age', type: 'NUM', health: 97.6, bins: ['18–24','25–31','32–38','39–45','46–52','53–59','60–66','67–73','74–80'], values: [320,450,620,870,1010,1180,1050,850,524], note: 'Age is broadly distributed; review missing entries before choosing a fill strategy.' },
      { name: 'tenure_months', type: 'NUM', health: 100, bins: ['0–8','9–16','17–24','25–32','33–40','41–48','49–56','57–64','65–72'], values: [1400,950,750,600,520,550,650,730,893], note: 'New and long-term customers form different groups worth comparing.' },
      { name: 'monthly_charges', type: 'NUM', health: 98, bins: ['$0–20','$21–40','$41–60','$61–80','$81–100','$101–120','$121+'], values: [520,840,1330,1850,1190,820,352], note: 'Most charges fall in the middle bands; investigate unusual high charges.' },
      { name: 'contract_type', type: 'CAT', health: 94, bins: ['Monthly','1 year','2 years'], values: [3400,1700,1520], note: 'Monthly contracts are the largest group; standardize labels before comparing groups.' },
      { name: 'churn', type: 'CAT', health: 100, bins: ['Stayed','Left'], values: [5174,1869], note: 'The target classes are imbalanced; compare rates instead of raw counts alone.' },
    ],
  },
  {
    name: 'Sales export', shortName: 'Sales', filename: 'sales_export.csv',
    rows: '24,816', quality: '87', missing: '3.2%', ideas: '12',
    priorities: ['Check unusually large orders.', 'Review missing shipping durations.', 'Normalize region labels before grouping.'],
    columns: [
      { name: 'order_value', type: 'NUM', health: 99, bins: ['$0–50','$51–100','$101–150','$151–200','$201–250','$251+'], values: [8200,6900,4600,2600,1600,668], note: 'Order values have a long upper tail; the median may describe a typical order better than the mean.' },
      { name: 'quantity', type: 'NUM', health: 100, bins: ['1','2','3','4','5','6+'], values: [10400,6800,3600,2100,1200,716], note: 'Small orders dominate; inspect larger quantities separately.' },
      { name: 'shipping_days', type: 'NUM', health: 92, bins: ['0–1','2–3','4–5','6–7','8–9','10+'], values: [2200,7400,6800,3800,1800,831], note: 'Missing shipping durations need a consistent treatment before comparing delivery performance.' },
      { name: 'region', type: 'CAT', health: 96, bins: ['North','South','East','West'], values: [6600,5800,5600,5823], note: 'Region sizes are similar; normalize spelling to avoid splitting one region into multiple categories.' },
      { name: 'returned', type: 'CAT', health: 100, bins: ['Kept','Returned'], values: [22976,1840], note: 'Returns are a small group; use rates when comparing regions or products.' },
    ],
  },
  {
    name: 'Sensor readings', shortName: 'Sensors', filename: 'sensor_readings.csv',
    rows: '10,080', quality: '96', missing: '1.1%', ideas: '9',
    priorities: ['Investigate extreme temperature readings.', 'Review missing sensor measurements.', 'Validate device status labels.'],
    columns: [
      { name: 'temperature', type: 'NUM', health: 99, bins: ['10–14°','15–19°','20–24°','25–29°','30–34°','35–39°','40°+'], values: [120,800,2050,3980,2010,800,219], note: 'Most temperatures sit near the center; extreme readings deserve a source check.' },
      { name: 'humidity', type: 'NUM', health: 98, bins: ['0–20%','21–40%','41–60%','61–80%','81–100%'], values: [400,1800,4200,2700,778], note: 'Humidity clusters in the middle range; check missing readings before filling gaps.' },
      { name: 'pressure', type: 'NUM', health: 100, bins: ['980–990','991–1000','1001–1010','1011–1020','1021–1030'], values: [550,1800,4600,2400,730], note: 'Pressure is concentrated near the center; compare unusual values with device logs.' },
      { name: 'device_type', type: 'CAT', health: 100, bins: ['Indoor','Outdoor','Industrial'], values: [4200,3600,2280], note: 'Device groups have different environments; compare their distributions separately.' },
      { name: 'status', type: 'CAT', health: 97, bins: ['Normal','Warning','Offline'], values: [8500,1000,278], note: 'Warnings and offline events are uncommon; validate status labels before counting incidents.' },
    ],
  },
]
