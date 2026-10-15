For the current moment, we have a Solar Power Plant to simulate

We've used a PVModule Datasheet for the main config values and tried to feasibly simulate the physics of a solar power plant

In the future, we'll add wind, natural gas and coal as a microgrid relies heavily on them

**Next Direction:**

```text
my-project/
│
│
├── MacroGraph/                      
│   ├── data_structs.py
│   ├── PRNG/                 # generate random graphs given a config
│   └── IngestGraph/          # interpretation of the graph and management of the energy flow in it
│
└──  MiniGraph/                       
    ├── Solar/
    ├── Wind/
    ├── Gas/                   
    └── Coal/                  
 
```