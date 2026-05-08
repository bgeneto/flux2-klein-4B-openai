

# How to Use Z‐Image on a GPU with Only 4GB VRAM

leejet stable-diffusion.cpp project now supports z-image-turbo, see PR #1020 in  https://github.com/leejet/stable-diffusion.cpp/pull/1020  

Github main project:

[leejet/stable-diffusion.cpp: Diffusion model(SD,Flux,Wan,Qwen Image,Z-Image,...) inference in pure C/C++](https://github.com/leejet/stable-diffusion.cpp) 



## Download Z-Image Turbo Quantized Weights

Source:
<https://huggingface.co/leejet/Z-Image-Turbo-GGUF/tree/main>
Recommended for 4GB VRAM:

## Download Quantized Qwen3-4B Weights

Source:
<https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/tree/main>
Compatible options for 4GB VRAM:

## Download VAE

<https://huggingface.co/black-forest-labs/FLUX.1-schnell/tree/main>

You may use:

## Example Command

`.\bin\Release\sd-cli.exe --diffusion-model z_image_turbo-Q3_K.gguf --vae ae.safetensors --llm Qwen3-4B-Instruct-2507-Q4_K_M.gguf -p "A cinematic, melancholic photograph of a solitary hooded figure walking through a sprawling, rain-slicked metropolis at night. The city lights are a chaotic blur of neon orange and cool blue, reflecting on the wet asphalt. The scene evokes a sense of being a single component in a vast machine. Superimposed over the image in a sleek, modern, slightly glitched font is the philosophical quote: 'THE CITY IS A CIRCUIT BOARD, AND I AM A BROKEN TRANSISTOR.' -- moody, atmospheric, profound, dark academic" --cfg-scale 1.0 -v --offload-to-cpu --diffusion-fa -H 1024 -W 512`

### Recommended Flags for Low VRAM

| Flag               | Description                                                  |
| ------------------ | ------------------------------------------------------------ |
| `--offload-to-cpu` | Loads weights into VRAM only during computation → significantly reduces VRAM usage with no speed loss |
| `--diffusion-fa`   | Enables Flash Attention → faster and more memory-efficient   |

`--offload-to-cpu`
`--diffusion-fa`

### Optional Optimizations (Useful for Large Resolution)

| Flag                | Function                                                     |
| ------------------- | ------------------------------------------------------------ |
| `--vae-conv-direct` | Reduces VRAM usage during VAE decoding                       |
| `--vae-tiling`      | Applies tiled VAE processing → much lower memory consumption |
| `--clip-on-cpu`     | Allows you to run Qwen-3 4B on the CPU, enabling you to work with models of higher precision |

`--vae-conv-direct`
`--vae-tiling`
`--clip-on-cpu`

More command-line parameters can be found at <https://github.com/leejet/stable-diffusion.cpp/tree/master/examples/cli>.

### Comparison of Different Quantization Types

| bf16 | q8\_0 | q6\_K | q5\_0 | q4\_K | q4\_0 | q3\_K | q2\_K |
| ---- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| bf16 | q8_0  | q6_K  | q5_0  | q4_K  | q4_0  | q3_K  | q2_K  |



### 