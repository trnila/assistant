<script>
    import { onMount, onDestroy } from "svelte";
    import { Fireworks } from "fireworks-js";

    let container;
    let fireworks;

    onMount(() => {
        fireworks = new Fireworks(container);
        fireworks.start();
    });

    onDestroy(() => {
        fireworks?.stop();
    });
</script>

<div bind:this={container} />

<style>
    div {
        top: 0;
        left: 0;
        position: fixed;
        width: 100%;
        height: 100%;
    }
</style>
